import json
import pytest
from models import Run, SimState
from tests.conftest import make_run, make_agent
from database import db


# ── Create ────────────────────────────────────────────────────────────────────

def test_create_run_requires_admin(client):
    res = client.post("/api/runs/", json={"name": "my-run"})
    assert res.status_code == 401


def test_create_run(admin, app):
    res = admin.post("/api/runs/", json={
        "name": "no-news-control",
        "model": "mistral-large-latest",
        "news_enabled": False,
        "agent_count": 10,
        "tick_limit": 500,
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["name"] == "no-news-control"
    assert data["status"] == "seeding"
    assert data["news_enabled"] is False

    with app.app_context():
        run = Run.query.filter_by(name="no-news-control").first()
        assert run is not None
        assert run.status == "seeding"


def test_create_run_requires_name(admin):
    res = admin.post("/api/runs/", json={"model": "mistral-large-latest"})
    assert res.status_code in (400, 500)


# ── List ──────────────────────────────────────────────────────────────────────

def test_list_runs_empty(client):
    res = client.get("/api/runs/")
    assert res.status_code == 200
    data = res.get_json()
    assert data["runs"] == []
    assert data["active_run_id"] is None


def test_list_runs_returns_all(client, app):
    with app.app_context():
        make_run("run-a", status="completed")
        make_run("run-b", status="ready")
        db.session.commit()

    res = client.get("/api/runs/")
    data = res.get_json()
    assert len(data["runs"]) == 2
    names = {r["name"] for r in data["runs"]}
    assert names == {"run-a", "run-b"}


def test_list_runs_includes_status(client, app):
    with app.app_context():
        make_run("r1", status="running")
        db.session.commit()

    res = client.get("/api/runs/")
    run = res.get_json()["runs"][0]
    assert run["status"] == "running"


# ── Activate ──────────────────────────────────────────────────────────────────

def test_activate_run(admin, app):
    with app.app_context():
        r1 = make_run("run-1", status="running")
        r2 = make_run("run-2", status="ready")
        state = SimState.get()
        state.run_id = r1.id
        state.is_running = True
        db.session.commit()
        r1_id, r2_id = r1.id, r2.id

    res = admin.post(f"/api/runs/{r2_id}/activate")
    assert res.status_code == 200

    with app.app_context():
        state = SimState.get()
        assert state.run_id == r2_id
        assert state.is_running is False
        r1 = db.session.get(Run, r1_id)
        assert r1.status == "stopped"
        r2 = db.session.get(Run, r2_id)
        assert r2.status == "running"


# ── Start / Stop ──────────────────────────────────────────────────────────────

def test_start_run(admin, app):
    with app.app_context():
        run = make_run("run-x", status="running")
        state = SimState.get()
        state.run_id = run.id
        db.session.commit()
        run_id = run.id

    res = admin.post(f"/api/runs/{run_id}/start")
    assert res.status_code == 200

    with app.app_context():
        state = SimState.get()
        assert state.is_running is True
        assert state.run_id == run_id


def test_stop_run(admin, app):
    with app.app_context():
        run = make_run("run-y", status="running")
        state = SimState.get()
        state.run_id = run.id
        state.is_running = True
        db.session.commit()
        run_id = run.id

    res = admin.post(f"/api/runs/{run_id}/stop")
    assert res.status_code == 200

    with app.app_context():
        state = SimState.get()
        assert state.is_running is False
        run = db.session.get(Run, run_id)
        assert run.status == "stopped"


def test_stop_run_does_not_advance_queue(admin, app):
    """Stopping a run should not auto-start the next queued run."""
    with app.app_context():
        r1 = make_run("run-active", status="running")
        r2 = make_run("run-next", status="ready")
        make_agent(r2.id, "agent1")
        state = SimState.get()
        state.run_id = r1.id
        state.is_running = True
        db.session.commit()
        r1_id, r2_id = r1.id, r2.id

    admin.post(f"/api/runs/{r1_id}/stop")

    with app.app_context():
        state = SimState.get()
        assert state.is_running is False
        r2 = db.session.get(Run, r2_id)
        assert r2.status == "ready"  # untouched


# ── Delete ────────────────────────────────────────────────────────────────────

def test_delete_requires_admin(client, app):
    with app.app_context():
        run = make_run("del-me", status="stopped")
        db.session.commit()
        run_id = run.id

    res = client.delete(f"/api/runs/{run_id}")
    assert res.status_code == 401


def test_delete_stopped_run(admin, app):
    with app.app_context():
        run = make_run("del-me", status="stopped")
        db.session.commit()
        run_id = run.id

    res = admin.delete(f"/api/runs/{run_id}")
    assert res.status_code == 200

    with app.app_context():
        assert db.session.get(Run, run_id) is None


def test_delete_running_run_blocked(admin, app):
    with app.app_context():
        run = make_run("live", status="running")
        state = SimState.get()
        state.run_id = run.id
        state.is_running = True
        db.session.commit()
        run_id = run.id

    res = admin.delete(f"/api/runs/{run_id}")
    assert res.status_code == 409

    with app.app_context():
        assert db.session.get(Run, run_id) is not None


def test_delete_last_run_clears_simstate(admin, app):
    """Deleting the only run should null out SimState.run_id."""
    with app.app_context():
        run = make_run("only-run", status="completed")
        state = SimState.get()
        state.run_id = run.id
        state.is_running = False
        db.session.commit()
        run_id = run.id

    res = admin.delete(f"/api/runs/{run_id}")
    assert res.status_code == 200

    with app.app_context():
        assert db.session.get(Run, run_id) is None
        state = SimState.get()
        assert state.run_id is None


def test_delete_cascades_agents_and_posts(admin, app):
    """Deleting a run removes all agents and their posts."""
    from models import Agent, Post
    with app.app_context():
        run = make_run("cascade-test", status="stopped")
        agent = make_agent(run.id, "testbot")
        db.session.add(Post(
            run_id=run.id, agent_id=agent.id,
            content="hello", tick_number=1,
        ))
        db.session.commit()
        run_id = run.id

    admin.delete(f"/api/runs/{run_id}")

    with app.app_context():
        assert db.session.get(Run, run_id) is None
        assert Agent.query.filter_by(run_id=run_id).count() == 0
        assert Post.query.filter_by(run_id=run_id).count() == 0
