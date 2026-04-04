import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from mistralai.client import Mistral
from mistralai.client.models import TextChunk

from config import Config
from database import db
from ipip import ITEMS, score_responses
from models import Agent, IpipResponse, NewsItem, PersonalitySnapshot, Post, Run, SimState
from news import get_headlines_for_agent

logger = logging.getLogger(__name__)


def _extract_text(content):
    """Extract plain text from a Mistral response content field (str | list | None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(c.text for c in content if isinstance(c, TextChunk))

# ── Rate limiter + retry (Mistral free tier: 1 req/sec) ──────────────────────

_rl_lock = threading.Lock()
_rl_next = 0.0  # monotonic time when next call is allowed


def _mistral_chat(client, messages, max_tokens, temperature):
    """Call Mistral with proactive throttling + exponential-backoff retry on 429."""
    global _rl_next
    max_retries = 6
    for attempt in range(max_retries):
        # Proactive throttle: serialise all threads through a 1/sec gate
        with _rl_lock:
            now = time.monotonic()
            wait = _rl_next - now
            if wait > 0:
                time.sleep(wait)
            _rl_next = time.monotonic() + (1.0 / Config.MISTRAL_RATE_LIMIT)

        try:
            return client.chat.complete(
                model=Config.MISTRAL_MODEL,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as exc:
            is_rate_limit = "429" in repr(exc) or "rate" in str(exc).lower()
            if is_rate_limit and attempt < max_retries - 1:
                backoff = 2 ** attempt  # 1 s, 2 s, 4 s, 8 s, 16 s, 32 s
                logger.warning("429 rate-limited (attempt %d/%d) — backing off %ds",
                               attempt + 1, max_retries, backoff)
                time.sleep(backoff)
            else:
                raise

# ── Tick overlap guard ────────────────────────────────────────────────────────
_tick_running = False
_tick_lock = threading.Lock()


# ── Public entry point ────────────────────────────────────────────────────────

def run_tick(app, force=False, force_ipip=False):
    """Advance the simulation by one tick. Called by APScheduler."""
    global _tick_running
    with _tick_lock:
        if _tick_running:
            logger.warning("tick skipped — previous tick still running")
            return
        _tick_running = True
    try:
        _run_tick_inner(app, force=force, force_ipip=force_ipip)
    except Exception:
        logger.exception("tick crashed")
    finally:
        with _tick_lock:
            _tick_running = False


def _run_tick_inner(app, force=False, force_ipip=False):
    with app.app_context():
        state = SimState.get()
        if not state.is_running and not force:
            return

        run = db.session.get(Run, state.run_id)
        run_id = state.run_id

        # Auto-stop when tick_limit reached
        tick = state.current_tick + 1
        if run and run.tick_limit and tick > run.tick_limit:
            logger.info("run %d tick_limit %d reached — stopping", run_id, run.tick_limit)
            state.is_running = False
            if run and not run.ended_at:
                from datetime import datetime
                run.ended_at = datetime.utcnow()
            db.session.commit()
            return

        logger.info("tick %d starting (run %d)", tick, run_id)

        news_enabled = run.news_enabled if run else True

        all_agents = Agent.query.filter_by(is_active=True, run_id=run_id).all()
        agents = random.sample(all_agents, min(Config.AGENTS_PER_TICK, len(all_agents)))
        do_ipip = force_ipip or (tick % Config.REASSESSMENT_INTERVAL == 0)

        # Ghost mode — all agents reply to the pinned post this tick, post stays in network
        ghost_post = None
        if state.ghost_post_id:
            gp = Post.query.get(state.ghost_post_id)
            if gp:
                ghost_post = {
                    "id":      gp.id,
                    "handle":  gp.agent.handle if gp.agent else "ghost",
                    "content": gp.content,
                }
                agents = all_agents  # override sample — every agent responds
                state.ghost_post_id = None  # fire once, then let it influence organically
                logger.info("ghost mode — all %d agents replying to post %d", len(agents), gp.id)

        # Snapshot data needed by worker threads before we leave the main session
        agent_snapshots = [_agent_snapshot(a, ghost_post=ghost_post, news_enabled=news_enabled) for a in agents]

        # Each worker opens its own app_context + db session
        def post_worker(snap):
            return _generate_post_isolated(app, snap)

        def ipip_worker(snap):
            return _ipip_assessment_isolated(app, snap)

        # ── Post generation — skip on IPIP ticks to avoid rate-limit pile-up ──
        if not do_ipip:
            post_results = {}
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as pool:
                futures = {pool.submit(post_worker, s): s["id"] for s in agent_snapshots}
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        post_results[agent_id] = future.result()
                    except Exception:
                        logger.exception("post generation failed for agent %d", agent_id)

            for agent_id, results in post_results.items():
                if not results:
                    continue
                for content, parent_id, news_context, engagement_type, prompt, is_public in results:
                    db.session.add(Post(
                        run_id=run_id,
                        agent_id=agent_id,
                        content=content,
                        tick_number=tick,
                        parent_id=parent_id,
                        news_context=news_context,
                        engagement_type=engagement_type,
                        prompt=prompt,
                        is_public=is_public,
                    ))
                    # Register any new headlines for semantic analysis
                    if news_context:
                        for h in news_context:
                            if h.get("url") and not NewsItem.query.filter_by(url=h["url"]).first():
                                db.session.add(NewsItem(
                                    run_id=run_id,
                                    url=h["url"], title=h["title"],
                                    summary=h.get("summary"),
                                    source=h.get("source"), category=h.get("category"),
                                ))

        # ── IPIP assessment (all active agents) ──────────────────────────────────
        if do_ipip:
            logger.info("tick %d: running IPIP assessments for all %d agents", tick, len(all_agents))
            all_ipip_snaps = [_ipip_snapshot(a) for a in all_agents]
            ipip_results = {}
            with ThreadPoolExecutor(max_workers=Config.IPIP_WORKERS) as pool:
                futures = {pool.submit(ipip_worker, s): s["id"] for s in all_ipip_snaps}
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        ipip_results[agent_id] = future.result()
                    except Exception:
                        logger.exception("IPIP assessment failed for agent %d", agent_id)

            for agent_id, result in ipip_results.items():
                if result is None:
                    continue
                scores, big_five, new_bio = result
                for idx, score in enumerate(scores):
                    db.session.add(IpipResponse(
                        run_id=run_id,
                        agent_id=agent_id, tick_number=tick,
                        item_number=idx + 1, score=score,
                    ))
                db.session.add(PersonalitySnapshot(
                    run_id=run_id,
                    agent_id=agent_id, tick_number=tick,
                    openness=big_five["O"], conscientiousness=big_five["C"],
                    extraversion=big_five["E"], agreeableness=big_five["A"],
                    neuroticism=big_five["N"],
                ))
                # Update agent's live scores and bio
                agent = db.session.get(Agent, agent_id)
                if agent:
                    agent.openness          = big_five["O"]
                    agent.conscientiousness = big_five["C"]
                    agent.extraversion      = big_five["E"]
                    agent.agreeableness     = big_five["A"]
                    agent.neuroticism       = big_five["N"]
                    agent.bio               = new_bio
                logger.info("IPIP done — agent %d tick %d: %s", agent_id, tick, big_five)
                logger.info("bio updated — agent %d: %s", agent_id, new_bio)

        state.current_tick = tick
        db.session.commit()
        logger.info("tick %d complete", tick)


# ── Agent snapshots ───────────────────────────────────────────────────────────

def _ipip_snapshot(agent):
    """Lightweight snapshot for IPIP — includes all recent thoughts (public + private) for grounding."""
    recent = (
        Post.query
        .filter_by(agent_id=agent.id)
        .order_by(Post.created_at.desc())
        .limit(20)
        .all()
    )
    return {
        "id":                agent.id,
        "name":              agent.name,
        "handle":            agent.handle,
        "bio":               agent.bio,
        "openness":          agent.openness,
        "conscientiousness": agent.conscientiousness,
        "extraversion":      agent.extraversion,
        "agreeableness":     agent.agreeableness,
        "neuroticism":       agent.neuroticism,
        "recent_posts":      [{"content": p.content, "is_public": p.is_public} for p in recent],
    }


def _agent_snapshot(agent, ghost_post=None, news_enabled=True):
    """Serialize agent state to a plain dict so worker threads don't touch the ORM."""
    followee_ids = [f.followee_id for f in agent.following]
    feed = (
        Post.query
        .filter(Post.agent_id.in_(followee_ids), Post.is_public == True)
        .order_by(Post.created_at.desc())
        .limit(Config.FEED_SAMPLE_SIZE)
        .all()
    ) if followee_ids else (
        Post.query
        .filter(Post.agent_id != agent.id, Post.is_public == True)
        .order_by(Post.created_at.desc())
        .limit(Config.FEED_SAMPLE_SIZE)
        .all()
    )
    # Ghost mode overrides normal reply selection — every agent must respond
    reply_to = None
    if ghost_post:
        reply_to = ghost_post
    elif feed and random.random() < 0.70:
        target = random.choice(feed)
        reply_to = {"id": target.id, "handle": target.agent.handle, "content": target.content}

    return {
        "id":                agent.id,
        "name":              agent.name,
        "handle":            agent.handle,
        "bio":               agent.bio,
        "openness":          agent.openness,
        "conscientiousness": agent.conscientiousness,
        "extraversion":      agent.extraversion,
        "agreeableness":     agent.agreeableness,
        "neuroticism":       agent.neuroticism,
        "feed":     [{"handle": p.agent.handle, "content": p.content} for p in feed],
        "reply_to": reply_to,
        # Replies never get headlines. Top-level posts get one 60% of the time — the rest post organically.
        "headlines": [] if (not news_enabled or reply_to or random.random() < 0.4) else get_headlines_for_agent(
            {"openness": agent.openness, "conscientiousness": agent.conscientiousness,
             "extraversion": agent.extraversion, "agreeableness": agent.agreeableness,
             "neuroticism": agent.neuroticism},
            n=1,
        ),
    }


# ── Isolated workers (each opens its own app_context) ────────────────────────

def _generate_post_isolated(app, snap):
    with app.app_context():
        return _generate_post(snap)


def _ipip_assessment_isolated(app, snap):
    with app.app_context():
        return _run_ipip_assessment(snap)


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _mistral_client():
    return Mistral(api_key=Config.MISTRAL_API_KEY)



def _build_system_prompt(snap):
    return (
        f"You are {snap['name']} (@{snap['handle']}), a user on a social media platform.\n\n"
        f"Bio: {snap['bio'] or 'No bio provided.'}"
    )



def _build_ipip_system_prompt(snap):
    """System prompt for IPIP assessment — name only, no platform framing or bio.
    The agent must derive its self-assessment purely from its posts and thoughts."""
    return f"You are {snap['name']} (@{snap['handle']})."


def _regenerate_bio(snap, client):
    """Regenerate the agent's bio from recent posts — no scores, purely behavioral."""
    recent = snap.get("recent_posts", [])
    if recent:
        posts_block = "\n".join(f'- "{p["content"]}"' for p in recent)
        context = f"Here are your recent posts and thoughts:\n{posts_block}\n\n"
    else:
        context = ""
    prompt = (
        f"You are {snap['name']} (@{snap['handle']}).\n\n"
        f"{context}"
        "Rewrite your bio in 1–2 sentences."
    )
    resp = _mistral_chat(
        client,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.9,
    )
    return _extract_text(resp.choices[0].message.content).strip().strip('"')


def _generate_thoughts(snap, client, user_prompt, n):
    """Generate n distinct thoughts in one call, separated by ---."""
    prompt = user_prompt + f"\n\nWrite {n} different thoughts, each 1–3 sentences. Separate them with ---"
    resp = _mistral_chat(
        client,
        messages=[
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=Config.MAX_POST_TOKENS * n,
        temperature=0.9,
    )
    raw = _extract_text(resp.choices[0].message.content).strip()
    thoughts = [re.sub(r'^\d+[\.\)]\s*', '', t.strip()) for t in raw.split("---") if t.strip()]
    return thoughts[:n] if thoughts else [raw]


def _select_thought(snap, thoughts, client):
    """Ask the agent which thought to post. Returns 0-based index of selected thought."""
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(thoughts))
    resp = _mistral_chat(
        client,
        messages=[
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": (
                f"You had these thoughts:\n\n{numbered}\n\n"
                "Which do you post? Reply with only the number."
            )},
        ],
        max_tokens=5,
        temperature=0.3,
    )
    raw = _extract_text(resp.choices[0].message.content).strip()
    digits = re.findall(r"\d", raw)
    if digits:
        idx = int(digits[0]) - 1
        if 0 <= idx < len(thoughts):
            return idx
    return 0


def _generate_post(snap):
    client = _mistral_client()

    headlines = snap.get("headlines", [])

    if snap["reply_to"]:
        # Replies are direct social responses — single generation, always public
        r = snap["reply_to"]
        user_prompt = f"@{r['handle']}: \"{r['content']}\""
        resp = _mistral_chat(
            client,
            messages=[
                {"role": "system", "content": _build_system_prompt(snap)},
                {"role": "user",   "content": user_prompt},
            ],
            max_tokens=Config.MAX_POST_TOKENS,
            temperature=0.9,
        )
        content = _extract_text(resp.choices[0].message.content).strip()
        return [(content, r["id"], None, "reply", user_prompt, True)]

    # Top-level posts: generate N thoughts, agent selects one to publish
    if headlines:
        h = headlines[0]
        user_prompt = f"[{h['source']} / {h['category']}] {h['title']}"
        if h.get("summary"):
            user_prompt += f"\n\n{h['summary']}"
        stored_headlines = headlines
        engagement_type = "news"
    elif snap["feed"]:
        user_prompt = "\n".join(f"@{p['handle']}: {p['content']}" for p in snap["feed"])
        stored_headlines = None
        engagement_type = "organic"
    else:
        user_prompt = ""
        stored_headlines = None
        engagement_type = "organic"

    thoughts = _generate_thoughts(snap, client, user_prompt, Config.N_THOUGHTS)
    selected_idx = _select_thought(snap, thoughts, client) if len(thoughts) > 1 else 0

    return [
        (
            thought,
            None,
            stored_headlines if i == selected_idx else None,
            engagement_type,
            user_prompt if i == selected_idx else None,
            i == selected_idx,
        )
        for i, thought in enumerate(thoughts)
    ]


def _run_ipip_assessment(snap):
    client = _mistral_client()
    items_block = "\n".join(f"{item['number']}. {item['text']}" for item in ITEMS)

    recent_posts = snap.get("recent_posts", [])
    if recent_posts:
        public   = [p for p in recent_posts if p["is_public"]]
        private  = [p for p in recent_posts if not p["is_public"]]
        block = ""
        if public:
            block += "Posts you made public:\n" + "\n".join(f'- "{p["content"]}"' for p in public) + "\n\n"
        if private:
            block += "Thoughts you kept to yourself:\n" + "\n".join(f'- "{p["content"]}"' for p in private) + "\n\n"
        context = (
            f"Here is your recent inner and outer life:\n{block}"
            "Rate how accurately each statement below describes you.\n\n"
        )
    else:
        context = ""

    user_prompt = (
        f"{context}"
        "Scale: 1 = Very Inaccurate, 2 = Moderately Inaccurate, "
        "3 = Neither, 4 = Moderately Accurate, 5 = Very Accurate\n\n"
        "Reply with ONLY a comma-separated list of 120 integers (e.g. 3,4,2,5,1,...).\n\n"
        f"Statements:\n{items_block}"
    )
    resp = _mistral_chat(
        client,
        messages=[
            {"role": "system", "content": _build_ipip_system_prompt(snap)},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    raw = _extract_text(resp.choices[0].message.content).strip()
    scores = _parse_ipip_response(raw, snap["id"])
    if scores is None:
        return None
    big_five = score_responses({i + 1: scores[i] for i in range(len(scores))})
    new_bio = _regenerate_bio(snap, client)
    return scores, big_five, new_bio


def _parse_ipip_response(raw, agent_id):
    # Extract all integers from the response — tolerates preamble/postamble text
    scores = [int(x) for x in re.findall(r"\b[1-5]\b", raw)]
    n = len(scores)
    if n < 60:
        logger.warning("Agent %d returned only %d IPIP scores — too few to score", agent_id, n)
        return None
    if n > 120:
        scores = scores[:120]
    if n != 120:
        logger.info("Agent %d returned %d/120 IPIP scores — scoring proportionally", agent_id, n)
    return scores


# ── News semantic analysis (Hugging Face Inference API) ──────────────────────

_HF_SENTIMENT_URL = "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
_HF_EMOTION_URL   = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"


def _hf_infer_batch(url, texts, headers, retries=3):
    """POST a batch of texts to a HF Inference API endpoint.
    Retries on HTTP 503, read timeouts, and 200+error-body (model still loading)."""
    from requests.exceptions import ReadTimeout
    for attempt in range(retries):
        wait = 20 * (attempt + 1)
        try:
            resp = requests.post(url, json={"inputs": texts}, headers=headers, timeout=30)
        except ReadTimeout:
            logger.info("HF read timeout (attempt %d/%d) — retrying in %ds", attempt + 1, retries, wait)
            time.sleep(wait)
            continue
        if resp.status_code == 503:
            logger.info("HF model loading (503) — retrying in %ds", wait)
            time.sleep(wait)
            continue
        resp.raise_for_status()
        result = resp.json()
        # HF sometimes returns 200 with {"error": "..."} while the model warms up
        if isinstance(result, dict) and "error" in result:
            logger.info("HF model loading (error body) — retrying in %ds", wait)
            time.sleep(wait)
            continue
        return result
    raise RuntimeError("HF model failed to load after retries")


def _analyze_news_batch(items, app):
    """Analyze a batch of (item_id, title, summary) tuples via HF Inference API and persist results.
    Two API calls total (sentiment + emotion) regardless of batch size."""
    key = Config.HF_API_KEY
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    # Use title + summary for richer signal; fall back to title alone if no summary
    texts = [
        f"{title}. {summary}".strip() if summary else title
        for _, title, summary in items
    ]
    try:
        sent_results = _hf_infer_batch(_HF_SENTIMENT_URL, texts, headers)
        emo_results  = _hf_infer_batch(_HF_EMOTION_URL,   texts, headers)
    except Exception:
        logger.exception("HF batch analysis failed")
        return

    # The serverless API packs all per-input top labels into a single inner list:
    # [[result_input0, result_input1, ...]] — so we index via [0][i].
    _SENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

    with app.app_context():
        for i, (item_id, title, _) in enumerate(items):
            sent = sent_results[0][i]
            emo  = emo_results[0][i]
            sentiment = round(_SENT_SCORE.get(sent["label"].lower(), 0.0), 4)
            emotion   = emo["label"].lower()
            item = db.session.get(NewsItem, item_id)
            if item:
                item.sentiment = sentiment
                item.emotion   = emotion
                item.analyzed  = True
                logger.info("news analyzed — %s → sentiment:%.2f emotion:%s",
                            title[:50], sentiment, emotion)
        db.session.commit()


def _analyze_post_batch(post_ids_and_texts, app):
    """Analyze a batch of (post_id, content) tuples via HF Inference API and persist results."""
    key = Config.HF_API_KEY
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    texts = [content for _, content in post_ids_and_texts]
    try:
        sent_results = _hf_infer_batch(_HF_SENTIMENT_URL, texts, headers)
        emo_results  = _hf_infer_batch(_HF_EMOTION_URL,   texts, headers)
    except Exception:
        logger.exception("HF post batch analysis failed")
        return

    _SENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

    with app.app_context():
        for i, (post_id, _) in enumerate(post_ids_and_texts):
            sent = sent_results[0][i]
            emo  = emo_results[0][i]
            sentiment = round(_SENT_SCORE.get(sent["label"].lower(), 0.0), 4)
            emotion   = emo["label"].lower()
            post = db.session.get(Post, post_id)
            if post:
                post.sentiment    = sentiment
                post.emotion      = emotion
                post.nlp_analyzed = True
        db.session.commit()
    logger.info("post NLP batch done — %d posts analyzed", len(post_ids_and_texts))


def start_post_analyzer(app):
    """Background thread: analyze unanalyzed public posts via HF Inference API."""
    if not Config.HF_API_KEY:
        return

    def loop():
        while True:
            time.sleep(45)
            with app.app_context():
                unanalyzed = (
                    Post.query
                    .filter_by(nlp_analyzed=False, is_public=True)
                    .filter(Post.parent_id.is_(None))  # top-level posts only
                    .order_by(Post.id)
                    .limit(10)
                    .all()
                )
                batch = [(p.id, p.content) for p in unanalyzed]
            if batch:
                _analyze_post_batch(batch, app)

    threading.Thread(target=loop, daemon=True).start()


def start_news_analyzer(app):
    """Background thread: analyze unanalyzed news items via HF Inference API."""
    if not Config.HF_API_KEY:
        logger.info("HF_API_KEY not set — news sentiment analysis disabled")
        return

    def loop():
        while True:
            time.sleep(30)
            with app.app_context():
                unanalyzed = NewsItem.query.filter_by(analyzed=False).limit(5).all()
                items = [(i.id, i.title, i.summary) for i in unanalyzed]
            if items:
                _analyze_news_batch(items, app)

    threading.Thread(target=loop, daemon=True).start()
