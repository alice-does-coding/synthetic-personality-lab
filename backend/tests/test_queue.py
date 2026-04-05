"""Tests for the advance_queue() logic in isolation."""
import pytest
from models import Run, SimState
from simulation import advance_queue
from database import db
from tests.conftest import make_run, make_agent


def test_advance_queue_starts_next_ready_run(app):
    with app.app_context():
        run = make_run("next", status="ready")
        make_agent(run.id, "bot1")
        state = SimState.get()
        state.is_running = False
        state.run_id = None
        db.session.commit()
        run_id = run.id

        advance_queue()

        state = SimState.get()
        assert state.run_id == run_id
        assert state.is_running is True
        assert db.session.get(Run, run_id).status == "running"


def test_advance_queue_noop_when_already_running(app):
    with app.app_context():
        active = make_run("active", status="running")
        waiting = make_run("waiting", status="ready")
        make_agent(waiting.id, "bot2")
        state = SimState.get()
        state.run_id = active.id
        state.is_running = True
        db.session.commit()
        active_id = active.id
        waiting_id = waiting.id

        advance_queue()

        state = SimState.get()
        assert state.run_id == active_id  # unchanged
        assert db.session.get(Run, waiting_id).status == "ready"  # not started


def test_advance_queue_noop_when_no_ready_runs(app):
    with app.app_context():
        make_run("done", status="completed")
        state = SimState.get()
        state.is_running = False
        state.run_id = None
        db.session.commit()

        advance_queue()

        state = SimState.get()
        assert state.run_id is None
        assert state.is_running is False


def test_advance_queue_picks_oldest_ready_run(app):
    """Queue is FIFO — lowest id wins."""
    with app.app_context():
        r1 = make_run("first", status="ready")
        r2 = make_run("second", status="ready")
        make_agent(r1.id, "bot-a")
        make_agent(r2.id, "bot-b")
        state = SimState.get()
        state.is_running = False
        state.run_id = None
        db.session.commit()
        r1_id = r1.id

        advance_queue()

        state = SimState.get()
        assert state.run_id == r1_id


def test_completed_run_triggers_next(app):
    """Simulates what happens at tick_limit: run completes, next starts."""
    from datetime import datetime
    with app.app_context():
        r1 = make_run("finishing", status="running")
        r2 = make_run("queued", status="ready")
        make_agent(r2.id, "bot3")
        state = SimState.get()
        state.run_id = r1.id
        state.is_running = True
        db.session.commit()
        r1_id, r2_id = r1.id, r2.id

        # Simulate what simulation.py does at tick_limit
        r1.status = "completed"
        r1.ended_at = datetime.utcnow()
        state.is_running = False
        db.session.commit()

        advance_queue()

        state = SimState.get()
        assert state.run_id == r2_id
        assert state.is_running is True
        assert db.session.get(Run, r2_id).status == "running"
