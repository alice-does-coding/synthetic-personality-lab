import logging
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import llm
from providers.base import LLMAuthError

from config import Config
from database import db
from ipip import ITEMS, score_responses
from models import Agent, IpipResponse, NewsItem, PersonalitySnapshot, Post, Run
from news import get_headlines

logger = logging.getLogger(__name__)


def log_event(app, run_id, level, message, tick=None):
    """Append a RunEvent. Opens its own app context — safe to call from any thread."""
    try:
        with app.app_context():
            from models import RunEvent
            db.session.add(RunEvent(run_id=run_id, tick=tick, level=level, message=message))
            db.session.commit()
    except Exception:
        logger.warning("log_event failed (run %d): %s", run_id, message)


# ── Stats helpers — delegate to providers/mistral.py ─────────────────────────

def _reset_mistral_stats():
    from providers.mistral import reset_stats
    reset_stats()


def _read_mistral_stats():
    from providers.mistral import read_stats
    return read_stats()


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


def run_tick(app, run_id, force=False, force_ipip=False, skip_ipip=False):
    """Fire a single manual tick for a specific run. Skips if a tick is already in progress."""
    lock = _get_tick_lock(run_id)
    if not lock.acquire(blocking=False):
        logger.warning("manual tick skipped — run %d already ticking", run_id)
        return
    try:
        _run_tick_for_run(app, run_id, force=force, force_ipip=force_ipip, skip_ipip=skip_ipip)
    except LLMAuthError as exc:
        _fail_run(app, run_id, f"LLM API key invalid or credits exhausted: {exc}")
    except Exception:
        logger.exception("manual tick crashed for run %d", run_id)
    finally:
        lock.release()


# How many consecutive ticks with zero output before we declare the run failed.
_EMPTY_TICK_LIMIT = 3


def _fail_run(app, run_id, reason, tick=None):
    from datetime import datetime
    with app.app_context():
        run = db.session.get(Run, run_id)
        if run:
            run.status = "failed"
            run.error = reason
            run.ended_at = datetime.utcnow()
            db.session.commit()
    log_event(app, run_id, "error", reason, tick=tick)
    logger.error("run %d FAILED: %s", run_id, reason)


def _tick_loop_for_run(app, run_id):
    logger.info("tick loop started for run %d", run_id)
    consecutive_empty = 0
    current_tick = None

    while True:
        lock = _get_tick_lock(run_id)
        lock.acquire()
        produced = False
        fatal_reason = None
        try:
            produced, current_tick = _run_tick_for_run(app, run_id)
        except LLMAuthError as exc:
            fatal_reason = f"LLM API key invalid or credits exhausted: {exc}"
        except Exception:
            logger.exception("tick crashed for run %d", run_id)
        finally:
            lock.release()

        if fatal_reason:
            _fail_run(app, run_id, fatal_reason, tick=current_tick)
            break

        if produced is False:
            consecutive_empty += 1
            logger.warning("run %d: empty tick %d/%d", run_id, consecutive_empty, _EMPTY_TICK_LIMIT)
            log_event(app, run_id, "warning",
                      f"Empty tick ({consecutive_empty}/{_EMPTY_TICK_LIMIT}) — no output produced",
                      tick=current_tick)
            if consecutive_empty >= _EMPTY_TICK_LIMIT:
                _fail_run(app, run_id,
                    f"Halted after {_EMPTY_TICK_LIMIT} consecutive ticks with zero output. "
                    f"Check API key and model availability.",
                    tick=current_tick)
                break
        elif produced is True:
            consecutive_empty = 0
        # produced is None → tick was skipped (completed/stopped) — don't touch counter

        with app.app_context():
            run = db.session.get(Run, run_id)
            if not run or run.status != "running":
                if run and run.status == "stopped":
                    log_event(app, run_id, "info", "Run stopped manually", tick=current_tick)
                break
            interval = 0 if run.batch_mode else app.config["SIMULATION_TICK_SECONDS"]

        if interval > 0:
            time.sleep(interval)

    with _run_state_lock:
        _run_threads.pop(run_id, None)
    logger.info("tick loop exited for run %d", run_id)


def _run_tick_for_run(app, run_id, force=False, force_ipip=False, skip_ipip=False):
    """Run one tick. Returns (produced, tick) where produced is True/False/None (skipped)."""
    with app.app_context():
        run = db.session.get(Run, run_id)
        if not run:
            return None, None
        if not force and run.status != "running":
            return None, None

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
            # Count posts for the completion event
            from models import Post as _Post
            post_total = db.session.query(db.func.count(_Post.id)).filter_by(run_id=run_id, is_public=True).scalar() or 0
            log_event(app, run_id, "info",
                      f"Tick limit reached — run complete ({run.tick_limit} ticks, {post_total} posts)")
            return None, tick

        logger.info("tick %d starting (run %d)", tick, run_id)
        tick_start = time.monotonic()
        llm.reset_auth_latches(tick=tick)

        news_enabled = run.news_enabled

        all_agents = Agent.query.filter_by(is_active=True, run_id=run_id).all()
        cap = Config.AGENTS_PER_TICK
        agents = all_agents if cap == 0 else random.sample(all_agents, min(cap, len(all_agents)))
        do_ipip = (not skip_ipip) and (force_ipip or (tick % Config.REASSESSMENT_INTERVAL == 0))

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

        # Capture provider/model/behavior before leaving the main session
        run_provider       = run.provider
        run_model          = run.model
        run_behavior_model = run.behavior_model

        # Snapshot data needed by worker threads before we leave the main session
        feed_size = min(50, max(10, len(all_agents) // 3))

        agent_snapshots = [_agent_snapshot(a, ghost_post=ghost_post, news_enabled=news_enabled,
                                           provider=run_provider, model=run_model,
                                           behavior_model=run_behavior_model,
                                           feed_size=feed_size) for a in agents]

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
                    except (TypeError, AttributeError, LLMAuthError) as exc:
                        # Fatal errors — stop the run immediately
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
            all_ipip_snaps = [_ipip_snapshot(a, grounded=grounded,
                                              provider=run_provider, model=run_model) for a in all_agents]
            ipip_results = {}
            with ThreadPoolExecutor(max_workers=Config.IPIP_WORKERS) as pool:
                futures = {pool.submit(ipip_worker, s): s["id"] for s in all_ipip_snaps}
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        ipip_results[agent_id] = future.result()
                    except (TypeError, AttributeError, LLMAuthError) as exc:
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
                if any(big_five.get(k) is None for k in ("O", "C", "E", "A", "N")):
                    logger.warning("skipping snapshot for agent %d — incomplete big five: %s", agent_id, big_five)
                    continue
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

        # Only advance the tick counter if something was actually produced.
        snapshot_count = len([r for r in ipip_results.values() if r is not None]) if do_ipip else 0
        produced = post_count > 0 or snapshot_count > 0
        if produced:
            run.last_tick = tick
        else:
            logger.warning("tick %d produced nothing (run %d) — last_tick not advanced", tick, run_id)
        db.session.commit()

        # Log IPIP assessment milestones
        if do_ipip and snapshot_count > 0:
            log_event(app, run_id, "info",
                      f"IPIP assessment — {snapshot_count} agents scored",
                      tick=tick)

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

        return produced, tick


# ── Agent snapshots ───────────────────────────────────────────────────────────

def _ipip_snapshot(agent, grounded=True, provider="mistral", model=None):
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
        "provider":     provider,
        "model":        model or Config.MISTRAL_MODEL,
        "recent_posts": [{"content": p.content, "is_public": p.is_public} for p in recent],
    }


def _agent_snapshot(agent, ghost_post=None, news_enabled=True, provider="mistral", model=None, behavior_model=None, feed_size=None):
    """Serialize agent state to a plain dict so worker threads don't touch the ORM."""
    feed_size = feed_size or Config.FEED_SAMPLE_SIZE
    followee_ids = [f.followee_id for f in agent.following]

    # Chronological feed — most recent public posts from followees,
    # or from any other agent if this agent has no followees.
    feed_query = (
        Post.query
        .filter(Post.agent_id.in_(followee_ids), Post.is_public == True)
        if followee_ids
        else Post.query.filter(Post.agent_id != agent.id, Post.is_public == True)
    )
    candidates = feed_query.order_by(Post.created_at.desc()).limit(feed_size).all()
    feed_posts = [{"id": p.id, "content": p.content, "sentiment": p.sentiment} for p in candidates]

    # Ghost mode bypasses behavior model — every agent must respond to the pinned post
    if ghost_post:
        return {
            "id":                agent.id,
            "bio":               agent.bio,
            "openness":          agent.openness,
            "conscientiousness": agent.conscientiousness,
            "extraversion":      agent.extraversion,
            "agreeableness":     agent.agreeableness,
            "neuroticism":       agent.neuroticism,
            "provider":          provider,
            "model":             model or Config.MISTRAL_MODEL,
            "feed":              feed_posts,
            "reply_to":          ghost_post,
            "headlines":         [],
            "silent":            False,
        }

    reply_to = None
    headlines = []
    silent = False

    if behavior_model == "map":
        # B = MAP: personality × prompt → action
        from fogg import select_action
        candidate_headlines = get_headlines(n=3) if news_enabled else []

        agent_snap = {
            "openness": agent.openness, "conscientiousness": agent.conscientiousness,
            "extraversion": agent.extraversion, "agreeableness": agent.agreeableness,
            "neuroticism": agent.neuroticism,
        }
        action = select_action(agent_snap, feed_posts, candidate_headlines)

        if action is None:
            silent = True
        elif action["type"] == "reply":
            p = action["post"]
            # Dive into the thread — reply to a reply instead of the root post.
            # Extroverted, agreeable agents are most likely to join ongoing conversations.
            E = (agent.extraversion  or 50.0) / 100.0
            A = (agent.agreeableness or 62.0) / 100.0
            dive_p = 0.25 + (E * 0.25) + (A * 0.20)
            if random.random() < dive_p:
                thread_replies = (
                    Post.query
                    .filter(Post.parent_id == p["id"], Post.is_public == True)
                    .order_by(Post.created_at.desc())
                    .limit(5)
                    .all()
                )
                if thread_replies:
                    target = random.choice(thread_replies)
                    p = {"id": target.id, "content": target.content}
            reply_to = {"id": p["id"], "content": p["content"]}
        elif action["type"] == "news":
            headlines = [action["headline"]]
        # organic: reply_to and headlines stay empty

    else:
        # Random baseline (legacy behavior)
        if feed_posts and random.random() < 0.70:
            target = random.choice(feed_posts)
            reply_to = {"id": target["id"], "content": target["content"]}
        elif news_enabled and not reply_to and random.random() >= 0.4:
            headlines = get_headlines(n=1)

    return {
        "id":                agent.id,
        "bio":               agent.bio,
        "openness":          agent.openness,
        "conscientiousness": agent.conscientiousness,
        "extraversion":      agent.extraversion,
        "agreeableness":     agent.agreeableness,
        "neuroticism":       agent.neuroticism,
        "provider":          provider,
        "model":             model or Config.MISTRAL_MODEL,
        "feed":              feed_posts,
        "reply_to":          reply_to,
        "headlines":         headlines,
        "silent":            silent,
    }


# ── Isolated workers (each opens its own app_context) ────────────────────────

def _generate_post_isolated(app, snap):
    with app.app_context():
        return _generate_post(snap)


def _ipip_assessment_isolated(app, snap):
    with app.app_context():
        return _run_ipip_assessment(snap)


# ── LLM helpers ───────────────────────────────────────────────────────────────

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


def _generate_thoughts(snap, user_prompt, n):
    """Generate n distinct thoughts in one call, separated by |||."""
    provider = snap["provider"]
    model    = snap["model"]
    prompt = (
        user_prompt
        + f"\n\nRespond with {n} different thoughts, each under 280 characters. "
        "Separate them with ||| and nothing else. Output only the thoughts, no numbering, no quotes."
    )
    resp = llm.chat(
        provider,
        model,
        messages=[
            {"role": "system", "content": _build_system_prompt(snap)},
            {"role": "user",   "content": prompt},
        ],
        max_tokens=Config.MAX_POST_TOKENS * n,
        temperature=0.9,
    )
    raw = llm.extract_text(provider, resp.choices[0].message.content if hasattr(resp, "choices") else resp).strip()
    thoughts = [_clean_post(t) for t in raw.split("|||") if t.strip()]
    # fallback: if separator wasn't used, split on newlines
    if len(thoughts) < 2:
        thoughts = [_clean_post(t) for t in raw.splitlines() if t.strip()]
    thoughts = [t[:280] for t in thoughts if t]
    return thoughts[:n] if thoughts else [_clean_post(raw)[:280]]


def _generate_post(snap):
    if snap.get("silent"):
        return []

    provider = snap["provider"]
    model    = snap["model"]

    headlines = snap.get("headlines", [])

    if snap["reply_to"]:
        # Replies are direct social responses — single generation, always public
        r = snap["reply_to"]
        user_prompt = f"\"{r['content']}\""
        resp = llm.chat(
            provider,
            model,
            messages=[
                {"role": "system", "content": _build_system_prompt(snap)},
                {"role": "user",   "content": user_prompt + "\n\nReply in plain text, under 280 characters. No quotes around your reply."},
            ],
            max_tokens=Config.MAX_POST_TOKENS,
            temperature=0.9,
        )
        raw_content = resp.choices[0].message.content if hasattr(resp, "choices") else resp
        content = _clean_post(llm.extract_text(provider, raw_content))[:280]
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

    thoughts = _generate_thoughts(snap, user_prompt, Config.N_THOUGHTS)
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
    provider = snap["provider"]
    model    = snap["model"]
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
    resp = llm.chat_ipip(
        provider,
        model,
        messages=[
            {"role": "system", "content": _build_ipip_system_prompt(snap)},
            {"role": "user",   "content": user_prompt},
        ],
        max_tokens=1000,
        temperature=0.3,
    )
    raw_content = resp.choices[0].message.content if hasattr(resp, "choices") else resp
    raw = llm.extract_text(provider, raw_content).strip()
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


