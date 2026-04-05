"""Tests for agent API endpoints."""
from models import Run, Agent
from database import db
from tests.conftest import make_run, make_agent


def test_list_agents_empty(client, app):
    with app.app_context():
        run = make_run("r1", status="running")
        db.session.commit()
        run_id = run.id

    res = client.get(f"/api/agents/?run_id={run_id}")
    assert res.status_code == 200
    assert res.get_json() == []


def test_list_agents_scoped_to_run(client, app):
    with app.app_context():
        r1 = make_run("r1", status="running")
        r2 = make_run("r2", status="ready")
        make_agent(r1.id, "agent-r1")
        make_agent(r2.id, "agent-r2")
        db.session.commit()
        r1_id = r1.id

    res = client.get(f"/api/agents/?run_id={r1_id}")
    data = res.get_json()
    assert len(data) == 1
    assert data[0]["handle"] == "agent-r1"


def test_get_agent(client, app):
    with app.app_context():
        run = make_run("r1", status="running")
        agent = make_agent(run.id, "mybot")
        db.session.commit()
        agent_id = agent.id

    res = client.get(f"/api/agents/{agent_id}")
    assert res.status_code == 200
    data = res.get_json()
    assert data["handle"] == "mybot"
    assert "personality" in data


def test_get_agent_not_found(client):
    res = client.get("/api/agents/99999")
    assert res.status_code == 404


def test_personality_history_empty(client, app):
    with app.app_context():
        run = make_run("r1", status="running")
        agent = make_agent(run.id, "histbot")
        db.session.commit()
        agent_id = agent.id

    res = client.get(f"/api/agents/{agent_id}/personality")
    assert res.status_code == 200
    assert res.get_json() == []


def test_population_drift_empty(client, app):
    with app.app_context():
        run = make_run("r1", status="running")
        db.session.commit()
        run_id = run.id

    res = client.get(f"/api/agents/population?run_id={run_id}")
    assert res.status_code == 200
    assert res.get_json() == []
