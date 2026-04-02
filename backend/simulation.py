import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from mistralai import Mistral

from config import Config
from database import db
from ipip import ITEMS, score_responses
from models import Agent, IpipResponse, NewsItem, PersonalitySnapshot, Post, SimState
from news import get_headlines_for_agent

logger = logging.getLogger(__name__)

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

        tick = state.current_tick + 1
        logger.info("tick %d starting", tick)

        all_agents = Agent.query.filter_by(is_active=True).all()
        agents = random.sample(all_agents, min(Config.AGENTS_PER_TICK, len(all_agents)))
        do_ipip = force_ipip or (tick % Config.REASSESSMENT_INTERVAL == 0)

        # Snapshot data needed by worker threads before we leave the main session
        agent_snapshots = [_agent_snapshot(a) for a in agents]

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

            for agent_id, result in post_results.items():
                if result:
                    content, parent_id, news_context = result
                    db.session.add(Post(
                        agent_id=agent_id,
                        content=content,
                        tick_number=tick,
                        parent_id=parent_id,
                        news_context=news_context,
                    ))
                    # Register any new headlines for semantic analysis
                    if news_context:
                        for h in news_context:
                            if h.get("url") and not NewsItem.query.filter_by(url=h["url"]).first():
                                db.session.add(NewsItem(
                                    url=h["url"], title=h["title"],
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
                scores, big_five = result
                for idx, score in enumerate(scores):
                    db.session.add(IpipResponse(
                        agent_id=agent_id, tick_number=tick,
                        item_number=idx + 1, score=score,
                    ))
                db.session.add(PersonalitySnapshot(
                    agent_id=agent_id, tick_number=tick,
                    openness=big_five["O"], conscientiousness=big_five["C"],
                    extraversion=big_five["E"], agreeableness=big_five["A"],
                    neuroticism=big_five["N"],
                ))
                # Update agent's live scores
                agent = db.session.get(Agent, agent_id)
                if agent:
                    agent.openness          = big_five["O"]
                    agent.conscientiousness = big_five["C"]
                    agent.extraversion      = big_five["E"]
                    agent.agreeableness     = big_five["A"]
                    agent.neuroticism       = big_five["N"]
                logger.info("IPIP done — agent %d tick %d: %s", agent_id, tick, big_five)

        state.current_tick = tick
        db.session.commit()
        logger.info("tick %d complete", tick)


# ── Agent snapshots ───────────────────────────────────────────────────────────

def _ipip_snapshot(agent):
    """Lightweight snapshot for IPIP — includes recent posts for self-assessment grounding."""
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
        "recent_posts":      [p.content for p in recent],
    }


def _agent_snapshot(agent):
    """Serialize agent state to a plain dict so worker threads don't touch the ORM."""
    followee_ids = [f.followee_id for f in agent.following]
    feed = (
        Post.query
        .filter(Post.agent_id.in_(followee_ids))
        .order_by(Post.created_at.desc())
        .limit(Config.FEED_SAMPLE_SIZE)
        .all()
    ) if followee_ids else (
        Post.query
        .filter(Post.agent_id != agent.id)
        .order_by(Post.created_at.desc())
        .limit(Config.FEED_SAMPLE_SIZE)
        .all()
    )
    # 40% chance to reply to a random post from the feed (if any exist)
    reply_to = None
    if feed and random.random() < 0.70:
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
        # Don't inject new headlines into replies — replies should respond to the post, not the news
        "headlines": [] if reply_to else get_headlines_for_agent(
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


def _ocean_behavioral_cues(snap):
    O = snap.get("openness")          or 50
    C = snap.get("conscientiousness") or 50
    E = snap.get("extraversion")      or 50
    A = snap.get("agreeableness")     or 50
    N = snap.get("neuroticism")       or 50

    cues = []
    if O >= 70:
        cues.append("You make unexpected connections and go on tangents. Abstract ideas excite you.")
    elif O <= 30:
        cues.append("You're concrete and literal. You don't have time for vague philosophising.")

    if C >= 70:
        cues.append("You think before you post. You're precise and back up what you say.")
    elif C <= 30:
        cues.append("You post on impulse. You'll start a thought without knowing where it ends.")

    if E >= 70:
        cues.append("You're loud and want to be heard. Energetic, reactive, exclamation-point prone.")
    elif E <= 30:
        cues.append("You're terse. You post rarely and don't need replies. Short sentences.")

    if A >= 70:
        cues.append("You're careful not to offend. You hedge, see multiple sides, and stay warm.")
    elif A <= 30:
        cues.append("You don't soften your opinions. Blunt, skeptical, sometimes cutting.")

    if N >= 70:
        cues.append("You're emotionally reactive. Things get under your skin. You spiral and ruminate.")
    elif N <= 30:
        cues.append("You're unbothered. Stuff that stresses others out barely registers for you.")

    return "\n".join(f"- {c}" for c in cues) if cues else "- Write naturally."


def _build_system_prompt(snap):
    return (
        f"You are {snap['name']} (@{snap['handle']}), a user on a social media platform called Lurkr.\n\n"
        f"Bio: {snap['bio'] or 'No bio provided.'}\n\n"
        f"How you write (based on your personality):\n{_ocean_behavioral_cues(snap)}\n\n"
        "Write short posts (1–3 sentences). No hashtags. No @mentions. "
        "No meta-commentary about being an AI. Write as yourself, in first person. "
        "You can be funny, crude, anxious, blunt, warm, chaotic — whatever your personality calls for."
    )


def _generate_post(snap):
    client = _mistral_client()

    headlines = snap.get("headlines", [])
    news_block = ""
    if headlines:
        h = headlines[0]
        news_block = f"\nA headline you saw today: [{h['source']} / {h['category']}] {h['title']}\n"

    if snap["reply_to"]:
        r = snap["reply_to"]
        user_prompt = (
            f"You saw this post from @{r['handle']}:\n\n\"{r['content']}\"\n"
            f"{news_block}\n"
            "Write a short reply (1–3 sentences) in your own voice. "
            "Be direct — respond to what they actually said."
        )
        parent_id = r["id"]
    elif snap["feed"]:
        feed_lines = "\n".join(f"@{p['handle']}: {p['content']}" for p in snap["feed"])
        user_prompt = (
            f"Recent posts you've seen:\n\n{feed_lines}\n"
            f"{news_block}\n"
            "Write your next post. You can react to the news, to something someone said, or share whatever's on your mind."
        )
        parent_id = None
    else:
        user_prompt = (
            f"{news_block}\n"
            "Write your next post. React to something in the news or share whatever's on your mind."
        ).strip()
        parent_id = None

    resp = _mistral_chat(
        client,
        messages=[
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=150,
        temperature=0.9,
    )
    content = resp.choices[0].message.content.strip()
    stored_headlines = headlines if headlines else None
    return content, parent_id, stored_headlines


def _run_ipip_assessment(snap):
    client = _mistral_client()
    items_block = "\n".join(f"{item['number']}. {item['text']}" for item in ITEMS)

    recent_posts = snap.get("recent_posts", [])
    if recent_posts:
        posts_block = "\n".join(f'- "{p}"' for p in recent_posts)
        context = (
            f"Here are your recent posts on Lurkr:\n{posts_block}\n\n"
            "Reflect on how you've actually been thinking, feeling, and behaving based on those posts. "
            "Then rate how accurately each statement below describes you — let your recent behavior guide your answers, "
            "not just how you'd like to see yourself.\n\n"
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
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    raw = resp.choices[0].message.content.strip()
    scores = _parse_ipip_response(raw, snap["id"])
    if scores is None:
        return None
    big_five = score_responses({i + 1: scores[i] for i in range(len(scores))})
    return scores, big_five


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


# ── News semantic analysis ────────────────────────────────────────────────────

def _call_nlp_service(text):
    """Call the local NLP microservice. Returns (sentiment_score, emotion_label) or None."""
    import urllib.request, json as _json
    payload = _json.dumps({"text": text}).encode()
    req = urllib.request.Request(
        Config.NLP_SERVICE_URL + "/analyze",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        data = _json.loads(resp.read())
    sentiment = data["sentiment"]["score"]
    emotion   = data["emotion"]["label"]
    return sentiment, emotion


def _analyze_news_item(item_id, title, app):
    """Run sentiment + emotion analysis on a single headline via the NLP service."""
    with app.app_context():
        try:
            sentiment, emotion = _call_nlp_service(title)
            item = NewsItem.query.get(item_id)
            if item:
                item.sentiment = sentiment
                item.emotion   = emotion
                item.analyzed  = True
                db.session.commit()
                logger.info("news analyzed — %s → sentiment:%.2f emotion:%s", title[:50], sentiment, emotion)
        except Exception:
            logger.exception("news analysis failed for item %d", item_id)


def start_news_analyzer(app):
    """Background thread: analyze unanalyzed news items as they accumulate."""
    def loop():
        while True:
            time.sleep(30)
            with app.app_context():
                unanalyzed = NewsItem.query.filter_by(analyzed=False).limit(5).all()
                items = [(i.id, i.title) for i in unanalyzed]
            for item_id, title in items:
                _analyze_news_item(item_id, title, app)

    t = threading.Thread(target=loop, daemon=True)
    t.start()
