"""
Permanent public run — the always-on public simulation.

One Run record lives forever with is_public=True. Public-run agents are regular
Agent rows with creator_token set. This module handles:

  - get_or_create_public_run()  — idempotent, safe to call on every boot
  - start_public_loop(app)      — dedicated tick thread, never stops
  - expire_agents(app, run)     — deactivate agents whose lifetime has ended
"""

import logging
import threading
import time

from config import Config
from database import db

logger = logging.getLogger(__name__)

PUBLIC_TICK_SECONDS      = 300   # 5 minutes between ticks
AGENT_LIFETIME_DAYS = 30  # agents live for 30 real-world days

_PUBLIC_RUN_NAME = "__simulation__"


def get_or_create_public_run(app):
    """
    Return the permanent public Run, creating it if it doesn't exist.
    Safe to call on every server boot.
    """
    from models import Run

    with app.app_context():
        run = Run.query.filter_by(is_public=True).first()
        if run:
            logger.info("public run found — id=%d last_tick=%d", run.id, run.last_tick)
            return run.id

        from datetime import datetime
        run = Run(
            name=_PUBLIC_RUN_NAME,
            description="Permanent public simulation — Synthetic Personality Lab.",
            model=Config.MISTRAL_POST_MODEL,
            provider="mistral",
            news_enabled=True,
            post_framing="a person on a social network",
            ipip_framing="your recent inner and outer life",
            seed_distribution="random",
            agent_count=0,
            tick_limit=None,        # never ends
            batch_mode=False,
            ipip_grounded=True,
            behavior_model="map",
            is_public=True,
            status="running",
            started_at=datetime.utcnow(),
        )
        db.session.add(run)
        db.session.commit()
        logger.info("public run created — id=%d", run.id)
        return run.id


def expire_agents(app, run_id):
    """Deactivate public-run agents whose 30-day wall-clock lifetime has ended."""
    from datetime import datetime
    from models import Agent

    now = datetime.utcnow()
    with app.app_context():
        expired = (
            Agent.query
            .filter_by(run_id=run_id, is_active=True)
            .filter(Agent.expires_at <= now)
            .filter(Agent.creator_token.isnot(None))
            .all()
        )
        if expired:
            for agent in expired:
                agent.is_active = False
                logger.info("public-run agent expired — handle=%s", agent.handle)
            db.session.commit()


def _public_tick_loop(app, run_id):
    """Dedicated tick loop for the public run. Runs forever."""
    from engine import _run_tick_for_run, run_intro_tick, log_event
    from providers.base import LLMAuthError

    logger.info("simulation tick loop started — run_id=%d", run_id)

    # Bootstrap — every agent gets a first-words intro post before regular ticks
    run_intro_tick(app, run_id)

    while True:
        try:
            with app.app_context():
                from models import Run
                run = db.session.get(Run, run_id)
                current_tick = (run.last_tick or 0) + 1

            produced, tick = _run_tick_for_run(app, run_id, force=True)

            if tick:
                expire_agents(app, run_id)

        except LLMAuthError as exc:
            logger.error("simulation tick auth error — sleeping 60s: %s", exc)
            time.sleep(60)
            continue
        except Exception:
            logger.exception("simulation tick crashed — sleeping 30s")
            time.sleep(30)
            continue

        time.sleep(PUBLIC_TICK_SECONDS)


def start_public_loop(app):
    """Start the simulation tick thread on server boot. No-op if already running."""
    from engine import _run_threads, _run_state_lock

    run_id = get_or_create_public_run(app)

    with _run_state_lock:
        existing = _run_threads.get(run_id)
        if existing and existing.is_alive():
            logger.info("simulation tick thread already alive — run_id=%d", run_id)
            return run_id

        t = threading.Thread(
            target=_public_tick_loop,
            args=(app, run_id),
            daemon=True,
            name="simulation-tick",
        )
        _run_threads[run_id] = t
        t.start()

    logger.info("simulation tick loop thread started")
    return run_id
