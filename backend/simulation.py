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
from models import Agent, IpipResponse, NewsItem, PersonalitySnapshot, Post, Run
from news import get_headlines_for_agent

logger = logging.getLogger(__name__)


def _extract_text(content):
    """Extract plain text from a Mistral response content field (str | list | None)."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(c.text for c in content if isinstance(c, TextChunk))

# ── Rate limiter + retry ──────────────────────────────────────────────────────

_rl_lock = threading.Lock()
_rl_next = 0.0  # monotonic time when next call is allowed

# Per-tick Mistral call stats (reset at tick start, accumulated across workers)
_stats_lock   = threading.Lock()
_stats_calls    = 0
_stats_throttle = 0.0   # total seconds spent waiting in the rate-limit gate
_stats_api      = 0.0   # total seconds spent waiting for Mistral to respond


def _reset_mistral_stats():
    global _stats_calls, _stats_throttle, _stats_api
    with _stats_lock:
        _stats_calls = _stats_throttle = _stats_api = 0


def _read_mistral_stats():
    with _stats_lock:
        return _stats_calls, _stats_throttle, _stats_api


def _mistral_chat(client, messages, max_tokens, temperature, model=None):
    """Call Mistral with proactive throttling + exponential-backoff retry on 429/5xx."""
    global _rl_next, _stats_calls, _stats_throttle, _stats_api
    model = model or Config.MISTRAL_MODEL
    max_retries = 6
    for attempt in range(max_retries):
        # Proactive throttle: serialise all threads through a shared gate
        with _rl_lock:
            now = time.monotonic()
            wait = _rl_next - now
            if wait > 0:
                time.sleep(wait)
                throttle_s = wait
            else:
                throttle_s = 0.0
            _rl_next = time.monotonic() + (1.0 / Config.MISTRAL_RATE_LIMIT)

        api_start = time.monotonic()
        try:
            resp = client.chat.complete(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            api_s = time.monotonic() - api_start
            with _stats_lock:
                _stats_calls    += 1
                _stats_throttle += throttle_s
                _stats_api      += api_s
            return resp
        except Exception as exc:
            err_str = repr(exc)
            is_rate_limit = "429" in err_str or "rate" in str(exc).lower()
            is_server_err = any(c in err_str for c in ("500", "502", "503", "504", "unavailable"))
            is_timeout    = any(c in err_str for c in ("ReadTimeout", "ConnectTimeout", "TimeoutError", "timed out", "timeout"))
            if (is_rate_limit or is_server_err or is_timeout) and attempt < max_retries - 1:
                backoff = 2 ** attempt
                logger.warning("Mistral error (attempt %d/%d) — backing off %ds: %s",
                               attempt + 1, max_retries, backoff, exc)
                time.sleep(backoff)
            else:
                raise

# ── Per-run thread management ─────────────────────────────────────────────────

_run_threads: dict = {}       # run_id → Thread
_run_tick_locks: dict = {}    # run_id → Lock (prevents overlap between loop + manual tick)
_run_state_lock = threading.Lock()


def _get_tick_lock(run_id):
    with _run_state_lock:
        if run_id not in _run_tick_locks:
            _run_tick_locks[run_id] = threading.Lock()
        return _run_tick_locks[run_id]


def start_run_thread(app, run_id):
    """Spawn a dedicated tick thread for run_id. No-op if one is already alive."""
    with _run_state_lock:
        existing = _run_threads.get(run_id)
        if existing and existing.is_alive():
            logger.info("run %d already has a live tick thread", run_id)
            return
        t = threading.Thread(
            target=_tick_loop_for_run,
            args=(app, run_id),
            daemon=True,
            name=f"tick-{run_id}",
        )
        _run_threads[run_id] = t
        t.start()
    logger.info("tick thread started for run %d", run_id)


def get_running_run_ids():
    """Return list of run IDs with live tick threads."""
    with _run_state_lock:
        return [rid for rid, t in _run_threads.items() if t.is_alive()]


def run_tick(app, run_id, force=False, force_ipip=False):
    """Fire a single manual tick for a specific run. Skips if a tick is already in progress."""
    lock = _get_tick_lock(run_id)
    if not lock.acquire(blocking=False):
        logger.warning("manual tick skipped — run %d already ticking", run_id)
        return
    try:
        _run_tick_for_run(app, run_id, force=force, force_ipip=force_ipip)
    except Exception:
        logger.exception("manual tick crashed for run %d", run_id)
    finally:
        lock.release()


def _tick_loop_for_run(app, run_id):
    logger.info("tick loop started for run %d", run_id)
    while True:
        lock = _get_tick_lock(run_id)
        lock.acquire()
        try:
            _run_tick_for_run(app, run_id)
        except Exception:
            logger.exception("tick crashed for run %d", run_id)
        finally:
            lock.release()

        with app.app_context():
            run = db.session.get(Run, run_id)
            if not run or run.status != "running":
                break
            interval = 0 if run.batch_mode else app.config["SIMULATION_TICK_SECONDS"]

        if interval > 0:
            time.sleep(interval)

    with _run_state_lock:
        _run_threads.pop(run_id, None)
    logger.info("tick loop exited for run %d", run_id)


def _run_tick_for_run(app, run_id, force=False, force_ipip=False):
    with app.app_context():
        run = db.session.get(Run, run_id)
        if not run:
            return
        if not force and run.status != "running":
            return

        tick = (run.last_tick or 0) + 1
        run_id = run.id  # ensure consistent

        # Auto-complete when tick_limit reached
        if run.tick_limit and tick > run.tick_limit:
            logger.info("run %d tick_limit %d reached — completing", run_id, run.tick_limit)
            from datetime import datetime
            run.status = "completed"
            if not run.ended_at:
                run.ended_at = datetime.utcnow()
            db.session.commit()
            return

        logger.info("tick %d starting (run %d)", tick, run_id)
        tick_start = time.monotonic()
        _reset_mistral_stats()

        news_enabled = run.news_enabled

        all_agents = Agent.query.filter_by(is_active=True, run_id=run_id).all()
        cap = Config.AGENTS_PER_TICK
        agents = all_agents if cap == 0 else random.sample(all_agents, min(cap, len(all_agents)))
        do_ipip = force_ipip or (tick % Config.REASSESSMENT_INTERVAL == 0)

        # Ghost mode — all agents reply to the pinned post this tick
        ghost_post = None
        if run.ghost_post_id:
            gp = db.session.get(Post, run.ghost_post_id)
            if gp:
                ghost_post = {"id": gp.id, "content": gp.content}
                agents = all_agents
                run.ghost_post_id = None  # fire once, then let it influence organically
                db.session.commit()
                logger.info("ghost mode — all %d agents replying to post %d", len(agents), gp.id)

        # Snapshot data needed by worker threads before we leave the main session
        agent_snapshots = [_agent_snapshot(a, ghost_post=ghost_post, news_enabled=news_enabled) for a in agents]

        # Each worker opens its own app_context + db session
        def post_worker(snap):
            return _generate_post_isolated(app, snap)

        def ipip_worker(snap):
            return _ipip_assessment_isolated(app, snap)

        # ── Post generation — skip on IPIP ticks to avoid rate-limit pile-up ──
        post_count = 0
        if not do_ipip:
            phase_start = time.monotonic()
            post_results = {}
            with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as pool:
                futures = {pool.submit(post_worker, s): s["id"] for s in agent_snapshots}
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        post_results[agent_id] = future.result()
                    except (TypeError, AttributeError) as exc:
                        # Programming error — not a transient API failure. Stop the run.
                        logger.critical("post generation fatal error for agent %d — halting run %d: %s", agent_id, run_id, exc)
                        raise
                    except Exception:
                        logger.exception("post generation failed for agent %d", agent_id)
            post_gen_s = time.monotonic() - phase_start

            db_start = time.monotonic()
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
                    if is_public:
                        post_count += 1
                    if news_context:
                        for h in news_context:
                            if h.get("url") and not NewsItem.query.filter_by(url=h["url"], run_id=run_id).first():
                                db.session.add(NewsItem(
                                    run_id=run_id,
                                    url=h["url"], title=h["title"],
                                    summary=h.get("summary"),
                                    source=h.get("source"), category=h.get("category"),
                                ))
            db_s = time.monotonic() - db_start

        # ── IPIP assessment (all active agents) ──────────────────────────────────
        if do_ipip:
            ipip_start = time.monotonic()
            logger.info("tick %d: running IPIP assessments for all %d agents", tick, len(all_agents))
            grounded = run.ipip_grounded if run.ipip_grounded is not None else True
            all_ipip_snaps = [_ipip_snapshot(a, grounded=grounded) for a in all_agents]
            ipip_results = {}
            with ThreadPoolExecutor(max_workers=Config.IPIP_WORKERS) as pool:
                futures = {pool.submit(ipip_worker, s): s["id"] for s in all_ipip_snaps}
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        ipip_results[agent_id] = future.result()
                    except (TypeError, AttributeError) as exc:
                        logger.critical("IPIP assessment fatal error for agent %d — halting run %d: %s", agent_id, run_id, exc)
                        raise
                    except Exception as exc:
                        logger.error("IPIP assessment failed for agent %d: %s: %s",
                                     agent_id, type(exc).__name__, exc)
            ipip_s = time.monotonic() - ipip_start

            db_start = time.monotonic()
            for agent_id, result in ipip_results.items():
                if result is None:
                    continue
                scores, big_five = result
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
                agent = db.session.get(Agent, agent_id)
                if agent:
                    agent.openness          = big_five["O"]
                    agent.conscientiousness = big_five["C"]
                    agent.extraversion      = big_five["E"]
                    agent.agreeableness     = big_five["A"]
                    agent.neuroticism       = big_five["N"]
            db_s = time.monotonic() - db_start

        run.last_tick = tick
        db.session.commit()

        total_s = time.monotonic() - tick_start
        ticks_per_hour = round(3600 / total_s) if total_s > 0 else "?"
        calls, throttle_s, api_s = _read_mistral_stats()
        avg_api_ms = round(api_s / calls * 1000) if calls else 0
        if do_ipip:
            logger.info(
                "tick %d done (run %d) — IPIP: %d agents, %.1fs total"
                "  [ipip: %.1fs, db: %.1fs]"
                "  mistral: %d calls, %.1fs throttle, %.1fs net, %dms avg"
                "  (~%s ticks/hr)",
                tick, run_id, len(all_agents), total_s,
                ipip_s, db_s,
                calls, throttle_s, api_s, avg_api_ms,
                ticks_per_hour,
            )
        else:
            logger.info(
                "tick %d done (run %d) — %d posts, %d agents, %.1fs total"
                "  [post_gen: %.1fs, db: %.1fs]"
                "  mistral: %d calls, %.1fs throttle, %.1fs net, %dms avg"
                "  (~%s ticks/hr)",
                tick, run_id, post_count, len(agents), total_s,
                post_gen_s, db_s,
                calls, throttle_s, api_s, avg_api_ms,
                ticks_per_hour,
            )


# ── Agent snapshots ───────────────────────────────────────────────────────────

def _ipip_snapshot(agent, grounded=True):
    """Snapshot for IPIP — recent posts are the grounding material when grounded=True."""
    recent = (
        Post.query
        .filter_by(agent_id=agent.id)
        .order_by(Post.created_at.desc())
        .limit(20)
        .all()
    ) if grounded else []
    return {
        "id":           agent.id,
        "grounded":     grounded,
        "recent_posts": [{"content": p.content, "is_public": p.is_public} for p in recent],
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
        reply_to = {"id": target.id, "content": target.content}

    return {
        "id":                agent.id,
        "bio":               agent.bio,
        "openness":          agent.openness,
        "conscientiousness": agent.conscientiousness,
        "extraversion":      agent.extraversion,
        "agreeableness":     agent.agreeableness,
        "neuroticism":       agent.neuroticism,
        "feed":     [{"content": p.content} for p in feed],
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

def _mistral_client(timeout_s=60):
    return Mistral(api_key=Config.MISTRAL_API_KEY, timeout_ms=timeout_s * 1000)


def _mistral_client_ipip():
    """Longer timeout for IPIP — 120-item prompts + recent posts take longer to generate."""
    return _mistral_client(timeout_s=120)



def _build_system_prompt(snap):
    return (
        f"About you: {snap['bio'] or 'No description available.'}\n\n"
        "When you post, write plain conversational text. "
        "No wrapping quotes. No markdown headers or bullet points. "
        "Do not count or annotate character length."
    )


def _build_ipip_system_prompt(snap):
    """System prompt for IPIP assessment — anonymous, no name/handle contamination.
    The agent must derive its self-assessment purely from its posts and thoughts."""
    return "Assess yourself based only on your recent posts and thoughts."


def _clean_post(text):
    """Strip common LLM formatting artifacts from a post."""
    t = text.strip()
    # Remove wrapping quotes (single or double)
    if len(t) >= 2 and t[0] in ('"', "'", "\u201c", "\u201d") and t[-1] in ('"', "'", "\u201c", "\u201d"):
        t = t[1:-1].strip()
    # Strip leading markdown decorators (* ** _) that never close
    t = re.sub(r'^[\*_]+\s*', '', t)
    # Strip trailing character-count annotations like (139) or [140]
    t = re.sub(r'\s*[\(\[]\d{1,3}[\)\]]\s*$', '', t)
    # Strip numbered list prefix if the model still adds one
    t = re.sub(r'^\d+[\.\)]\s*', '', t)
    return t.strip()


def _generate_thoughts(snap, client, user_prompt, n):
    """Generate n distinct thoughts in one call, separated by |||."""
    prompt = (
        user_prompt
        + f"\n\nRespond with {n} different thoughts, each under 140 characters. "
        "Separate them with ||| and nothing else. Output only the thoughts, no numbering, no quotes."
    )
    resp = _mistral_chat(
        client,
        messages=[
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=Config.MAX_POST_TOKENS * n,
        temperature=0.9,
        model=Config.MISTRAL_POST_MODEL,
    )
    raw = _extract_text(resp.choices[0].message.content).strip()
    thoughts = [_clean_post(t) for t in raw.split("|||") if t.strip()]
    # fallback: if separator wasn't used, split on newlines
    if len(thoughts) < 2:
        thoughts = [_clean_post(t) for t in raw.splitlines() if t.strip()]
    thoughts = [t[:140] for t in thoughts if t]
    return thoughts[:n] if thoughts else [_clean_post(raw)[:140]]


def _generate_post(snap):
    client = _mistral_client()

    headlines = snap.get("headlines", [])

    if snap["reply_to"]:
        # Replies are direct social responses — single generation, always public
        r = snap["reply_to"]
        user_prompt = f"\"{r['content']}\""
        resp = _mistral_chat(
            client,
            messages=[
                {"role": "system", "content": _build_system_prompt(snap)},
                {"role": "user",   "content": user_prompt + "\n\nReply in plain text, under 140 characters. No quotes around your reply."},
            ],
            max_tokens=Config.MAX_POST_TOKENS,
            temperature=0.9,
            model=Config.MISTRAL_POST_MODEL,
        )
        content = _clean_post(_extract_text(resp.choices[0].message.content))[:140]
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
        user_prompt = "\n".join(f'"{p["content"]}"' for p in snap["feed"])
        stored_headlines = None
        engagement_type = "organic"
    else:
        user_prompt = ""
        stored_headlines = None
        engagement_type = "organic"

    thoughts = _generate_thoughts(snap, client, user_prompt, Config.N_THOUGHTS)
    selected_idx = 0

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
    client = _mistral_client_ipip()
    items_block = "\n".join(f"{item['number']}. {item['text']}" for item in ITEMS)

    recent_posts = snap.get("recent_posts", []) if snap.get("grounded", True) else []
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
        # Ungrounded condition (H2 control) or tick-0 baseline — no behavioral evidence
        context = "Rate how accurately each statement below describes you.\n\n"

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


# ── News semantic analysis (Hugging Face Inference API) ──────────────────────

_HF_SENTIMENT_URL = "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
_HF_EMOTION_URL   = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"


def _hf_infer_batch(url, texts, headers, retries=6):
    """POST a batch of texts to a HF Inference API endpoint.
    Retries on any transient error (5xx, timeouts, model-loading error body)."""
    from requests.exceptions import ConnectionError as ReqConnError, ReadTimeout, Timeout
    for attempt in range(retries):
        backoff = min(20 * (attempt + 1), 60)
        try:
            resp = requests.post(url, json={"inputs": texts}, headers=headers, timeout=30)
        except (ReadTimeout, Timeout, ReqConnError) as exc:
            logger.warning("HF request error (attempt %d/%d) — retrying in %ds: %s",
                           attempt + 1, retries, backoff, exc)
            time.sleep(backoff)
            continue
        if resp.status_code in (500, 502, 503, 504):
            logger.warning("HF HTTP %d (attempt %d/%d) — retrying in %ds",
                           resp.status_code, attempt + 1, retries, backoff)
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        result = resp.json()
        # HF sometimes returns 200 with {"error": "..."} while the model warms up
        if isinstance(result, dict) and "error" in result:
            logger.warning("HF error body (attempt %d/%d) — retrying in %ds: %s",
                           attempt + 1, retries, backoff, result["error"])
            time.sleep(backoff)
            continue
        return result
    raise RuntimeError(f"HF inference failed after {retries} attempts")


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
