"""
Route-level tests for /api/arcade/* endpoints.

Tests the full HTTP stack: validation, persistence, and response shape.
LLM bio generation is patched throughout.
"""

import uuid
from unittest.mock import patch

import pytest
from app import create_app
from database import db as _db
from tests.conftest import TestConfig


@pytest.fixture(scope="session")
def app():
    return create_app(TestConfig)


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        from arcade_run import get_or_create_arcade_run
        get_or_create_arcade_run(app)
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def payload(**overrides):
    base = {
        "name": "Neon Ghost",
        "description": "A brooding wanderer who haunts the edges of conversations.",
        "creator_token": str(uuid.uuid4()),
    }
    base.update(overrides)
    return base


# ── POST /api/arcade/agents ───────────────────────────────────────────────────

def test_create_agent_returns_201(client):
    with patch("arcade._generate_bio", return_value="A haunting presence."):
        resp = client.post("/api/arcade/agents", json=payload())
    assert resp.status_code == 201


def test_create_agent_response_shape(client):
    with patch("arcade._generate_bio", return_value="A haunting presence."):
        resp = client.post("/api/arcade/agents", json=payload())
    data = resp.get_json()
    for key in ("id", "name", "handle", "bio", "creator_token", "origin_description",
                "expires_at", "is_active", "personality", "created_at"):
        assert key in data, f"Missing key: {key}"
    for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
        assert trait in data["personality"]


def test_create_agent_name_in_response(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(name="Cosmo Unit"))
    assert resp.get_json()["name"] == "Cosmo Unit"


def test_create_agent_bio_from_llm(client):
    with patch("arcade._generate_bio", return_value="Generated bio text."):
        resp = client.post("/api/arcade/agents", json=payload())
    assert resp.get_json()["bio"] == "Generated bio text."


def test_create_agent_missing_token_returns_400(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(creator_token=""))
    assert resp.status_code == 400


def test_create_agent_missing_token_field_returns_400(client):
    p = payload()
    del p["creator_token"]
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=p)
    assert resp.status_code == 400


def test_create_agent_empty_name_returns_400(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(name=""))
    assert resp.status_code == 400


def test_create_agent_name_too_long_returns_400(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(name="x" * 51))
    assert resp.status_code == 400


def test_create_agent_description_too_short_returns_400(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(description="short"))
    assert resp.status_code == 400


def test_create_agent_description_too_long_returns_400(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(description="x" * 501))
    assert resp.status_code == 400


def test_duplicate_token_returns_400(client):
    t = str(uuid.uuid4())
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload(creator_token=t))
        resp = client.post("/api/arcade/agents", json=payload(creator_token=t, name="Clone"))
    assert resp.status_code == 400
    assert "already have an agent" in resp.get_json()["error"]


def test_error_response_has_error_key(client):
    with patch("arcade._generate_bio", return_value="bio"):
        resp = client.post("/api/arcade/agents", json=payload(name=""))
    assert "error" in resp.get_json()


# ── GET /api/arcade/agents ────────────────────────────────────────────────────

def test_list_agents_empty(client):
    resp = client.get("/api/arcade/agents")
    assert resp.status_code == 200
    assert resp.get_json() == []


def test_list_agents_returns_created(client):
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload())
        client.post("/api/arcade/agents", json=payload())
    resp = client.get("/api/arcade/agents")
    assert resp.status_code == 200
    assert len(resp.get_json()) == 2


def test_list_agents_only_active(client, app):
    from models import Agent
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload())
    with app.app_context():
        a = Agent.query.filter(Agent.creator_token.isnot(None)).first()
        a.is_active = False
        _db.session.commit()
    resp = client.get("/api/arcade/agents")
    assert resp.get_json() == []


def test_list_agents_newest_first(client):
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload(name="First"))
        client.post("/api/arcade/agents", json=payload(name="Second"))
    resp = client.get("/api/arcade/agents")
    names = [a["name"] for a in resp.get_json()]
    assert names[0] == "Second"


# ── GET /api/arcade/agents/mine ───────────────────────────────────────────────

def test_mine_returns_agent(client):
    t = str(uuid.uuid4())
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload(creator_token=t))
    resp = client.get(f"/api/arcade/agents/mine?creator_token={t}")
    assert resp.status_code == 200
    assert resp.get_json()["creator_token"] == t


def test_mine_returns_null_when_not_found(client):
    resp = client.get(f"/api/arcade/agents/mine?creator_token={uuid.uuid4()}")
    assert resp.status_code == 200
    assert resp.get_json() is None


def test_mine_missing_token_returns_400(client):
    resp = client.get("/api/arcade/agents/mine")
    assert resp.status_code == 400


def test_mine_inactive_agent_not_returned(client, app):
    from models import Agent
    t = str(uuid.uuid4())
    with patch("arcade._generate_bio", return_value="bio"):
        client.post("/api/arcade/agents", json=payload(creator_token=t))
    with app.app_context():
        a = Agent.query.filter_by(creator_token=t).first()
        a.is_active = False
        _db.session.commit()
    resp = client.get(f"/api/arcade/agents/mine?creator_token={t}")
    assert resp.get_json() is None
