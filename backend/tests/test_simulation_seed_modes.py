"""
Tests for public-run agent creation seed modes.

Covers the three seed paths added to POST /api/simulation/agents:
  describe — name + description → LLM bio + random OCEAN  (default / legacy)
  random   — LLM generates name, bio, and OCEAN            (surprise me)
  scratch  — caller supplies name, bio, and OCEAN directly (full control)

LLM calls are patched throughout so tests stay fast and deterministic.
"""

import uuid
from unittest.mock import patch

import pytest
from app import create_app
from database import db as _db
from tests.conftest import TestConfig

_RANDOM_AGENT = (
    "Priya Nair",
    "I argue with economists online before my morning chai.",
    {
        "openness": 78.0,
        "conscientiousness": 42.0,
        "extraversion": 55.0,
        "agreeableness": 48.0,
        "neuroticism": 67.0,
    },
)


@pytest.fixture(scope="session")
def app():
    return create_app(TestConfig)


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        from simulation_run import get_or_create_public_run
        get_or_create_public_run(app)
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def token():
    return str(uuid.uuid4())


def scratch_payload(**overrides):
    base = {
        "creator_token":    token(),
        "seed_mode":        "scratch",
        "name":             "Zephyr Moss",
        "bio":              "Former librarian turned competitive eater. I contain multitudes.",
        "openness":         82,
        "conscientiousness": 31,
        "extraversion":     74,
        "agreeableness":    58,
        "neuroticism":      45,
    }
    base.update(overrides)
    return base


# ── Seed mode: describe (default / legacy) ────────────────────────────────────

class TestDescribeMode:
    def test_omitted_seed_mode_defaults_to_describe(self, client):
        with patch("simulation._generate_bio", return_value="A bio."):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "name":          "Echo Delta",
                "description":   "A restless signal bouncing through empty spaces.",
            })
        assert resp.status_code == 201

    def test_explicit_describe_mode(self, client):
        with patch("simulation._generate_bio", return_value="A bio."):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "describe",
                "name":          "Echo Delta",
                "description":   "A restless signal bouncing through empty spaces.",
            })
        assert resp.status_code == 201

    def test_describe_bio_comes_from_llm(self, client):
        with patch("simulation._generate_bio", return_value="Haunting the margins."):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "name":          "Wraith",
                "description":   "A wanderer who prefers shadows to spotlight.",
            })
        assert resp.get_json()["bio"] == "Haunting the margins."

    def test_describe_missing_name_returns_400(self, client):
        with patch("simulation._generate_bio", return_value="bio"):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "describe",
                "description":   "At least ten characters here.",
            })
        assert resp.status_code == 400

    def test_describe_short_description_returns_400(self, client):
        with patch("simulation._generate_bio", return_value="bio"):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "describe",
                "name":          "Someone",
                "description":   "short",
            })
        assert resp.status_code == 400


# ── Seed mode: random ─────────────────────────────────────────────────────────

class TestRandomMode:
    def test_random_returns_201(self, client):
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        assert resp.status_code == 201

    def test_random_response_shape(self, client):
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        data = resp.get_json()
        for key in ("id", "name", "handle", "bio", "creator_token",
                    "expires_at", "is_active", "personality", "created_at"):
            assert key in data, f"Missing key: {key}"
        for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            assert trait in data["personality"]

    def test_random_uses_llm_name_and_bio(self, client):
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        data = resp.get_json()
        assert data["name"] == "Priya Nair"
        assert data["bio"]  == "I argue with economists online before my morning chai."

    def test_random_uses_llm_ocean_scores(self, client):
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        p = resp.get_json()["personality"]
        assert p["openness"]          == 78.0
        assert p["conscientiousness"] == 42.0
        assert p["neuroticism"]       == 67.0

    def test_random_no_extra_fields_needed(self, client):
        """Only creator_token + seed_mode required — no name or description."""
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        assert resp.status_code == 201

    def test_random_duplicate_token_rejected(self, client):
        t = token()
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            client.post("/api/simulation/agents", json={"creator_token": t, "seed_mode": "random"})
            resp = client.post("/api/simulation/agents", json={"creator_token": t, "seed_mode": "random"})
        assert resp.status_code == 400
        assert "already have an agent" in resp.get_json()["error"]

    def test_random_origin_description_is_null(self, client):
        with patch("simulation._generate_random_agent", return_value=_RANDOM_AGENT):
            resp = client.post("/api/simulation/agents", json={
                "creator_token": token(),
                "seed_mode":     "random",
            })
        assert resp.get_json()["origin_description"] is None


# ── Seed mode: scratch ────────────────────────────────────────────────────────

class TestScratchMode:
    def test_scratch_returns_201(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload())
        assert resp.status_code == 201

    def test_scratch_preserves_name_and_bio(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(
            name="Zephyr Moss",
            bio="Former librarian turned competitive eater. I contain multitudes.",
        ))
        data = resp.get_json()
        assert data["name"] == "Zephyr Moss"
        assert data["bio"]  == "Former librarian turned competitive eater. I contain multitudes."

    def test_scratch_preserves_ocean_scores(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(
            openness=82, conscientiousness=31, extraversion=74,
            agreeableness=58, neuroticism=45,
        ))
        p = resp.get_json()["personality"]
        assert p["openness"]          == 82.0
        assert p["conscientiousness"] == 31.0
        assert p["extraversion"]      == 74.0
        assert p["agreeableness"]     == 58.0
        assert p["neuroticism"]       == 45.0

    def test_scratch_accepts_float_ocean(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(openness=72.5))
        assert resp.status_code == 201
        assert resp.get_json()["personality"]["openness"] == 72.5

    def test_scratch_missing_name_returns_400(self, client):
        p = scratch_payload()
        del p["name"]
        resp = client.post("/api/simulation/agents", json=p)
        assert resp.status_code == 400

    def test_scratch_empty_name_returns_400(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(name=""))
        assert resp.status_code == 400

    def test_scratch_name_too_long_returns_400(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(name="x" * 51))
        assert resp.status_code == 400

    def test_scratch_missing_bio_returns_400(self, client):
        p = scratch_payload()
        del p["bio"]
        resp = client.post("/api/simulation/agents", json=p)
        assert resp.status_code == 400

    def test_scratch_empty_bio_returns_400(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(bio=""))
        assert resp.status_code == 400

    def test_scratch_missing_ocean_trait_returns_400(self, client):
        p = scratch_payload()
        del p["openness"]
        resp = client.post("/api/simulation/agents", json=p)
        assert resp.status_code == 400
        assert "openness" in resp.get_json()["error"]

    def test_scratch_ocean_below_zero_returns_400(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(neuroticism=-1))
        assert resp.status_code == 400

    def test_scratch_ocean_above_100_returns_400(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(extraversion=101))
        assert resp.status_code == 400

    def test_scratch_ocean_boundary_zero_accepted(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(openness=0))
        assert resp.status_code == 201

    def test_scratch_ocean_boundary_100_accepted(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload(conscientiousness=100))
        assert resp.status_code == 201

    def test_scratch_duplicate_token_rejected(self, client):
        t = token()
        client.post("/api/simulation/agents", json=scratch_payload(creator_token=t))
        resp = client.post("/api/simulation/agents", json=scratch_payload(creator_token=t))
        assert resp.status_code == 400

    def test_scratch_no_llm_called(self, client):
        """Scratch mode must not touch the LLM at all."""
        with patch("simulation._generate_bio", side_effect=AssertionError("LLM called in scratch mode")):
            with patch("simulation._generate_random_agent", side_effect=AssertionError("LLM called in scratch mode")):
                resp = client.post("/api/simulation/agents", json=scratch_payload())
        assert resp.status_code == 201

    def test_scratch_origin_description_is_null(self, client):
        resp = client.post("/api/simulation/agents", json=scratch_payload())
        assert resp.get_json()["origin_description"] is None


# ── Invalid seed_mode ─────────────────────────────────────────────────────────

def test_invalid_seed_mode_returns_400(client):
    resp = client.post("/api/simulation/agents", json={
        "creator_token": token(),
        "seed_mode":     "vibes_only",
    })
    assert resp.status_code == 400
    assert "seed_mode" in resp.get_json()["error"]
