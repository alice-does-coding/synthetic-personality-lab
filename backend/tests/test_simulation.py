"""
Unit tests for simulation.py — agent generation service.

Tests validation, token enforcement, handle generation, and OCEAN sampling.
LLM bio generation is patched out — we're testing the service layer, not the model.
"""

import uuid
from unittest.mock import patch

import pytest
from app import create_app
from database import db as _db
from models import Agent
from tests.conftest import TestConfig


@pytest.fixture(scope="session")
def app():
    return create_app(TestConfig)


@pytest.fixture(autouse=True)
def db(app):
    with app.app_context():
        _db.create_all()
        # Ensure public run exists for every test
        from simulation_run import get_or_create_public_run
        get_or_create_public_run(app)
        yield _db
        _db.session.remove()
        _db.drop_all()


def token():
    return str(uuid.uuid4())


def make_agent(app, name="Test Agent", description="A curious entity who wanders digital spaces.", creator_token=None):
    """Call create_agent with bio generation patched out."""
    creator_token = creator_token or token()
    with app.app_context():
        with patch("simulation._generate_bio", return_value="A curious entity."):
            from simulation import create_agent
            return create_agent(creator_token, name=name, description=description), creator_token


# ── Validation ────────────────────────────────────────────────────────────────

def test_empty_name_raises(app):
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="Name"):
                create_agent(token(), name="", description="A valid description here.")


def test_name_too_long_raises(app):
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="Name"):
                create_agent(token(), name="x" * 51, description="A valid description here.")


def test_description_too_short_raises(app):
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="Description"):
                create_agent(token(), name="Valid Name", description="too short")


def test_description_too_long_raises(app):
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="Description"):
                create_agent(token(), name="Valid Name", description="x" * 501)


def test_missing_creator_token_raises(app):
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="creator_token"):
                create_agent("", name="Valid Name", description="A valid description here.")


# ── One agent per token ───────────────────────────────────────────────────────

def test_one_agent_per_token(app):
    agent, t = make_agent(app)
    with app.app_context():
        with patch("simulation._generate_bio", return_value="bio"):
            from simulation import create_agent
            with pytest.raises(ValueError, match="already have an agent"):
                create_agent(t, name="Another", description="A valid description here.")


def test_different_tokens_can_each_create(app):
    make_agent(app, name="Agent One")
    make_agent(app, name="Agent Two")
    with app.app_context():
        count = Agent.query.filter(Agent.creator_token.isnot(None)).count()
        assert count == 2


# ── Handle generation ─────────────────────────────────────────────────────────

def test_handle_derived_from_name(app):
    make_agent(app, name="Neon Rabbit")
    with app.app_context():
        a = Agent.query.filter(Agent.creator_token.isnot(None)).first()
        assert "neon" in a.handle or "rabbit" in a.handle


def test_handle_collision_resolved(app):
    make_agent(app, name="Luna")
    make_agent(app, name="Luna")
    with app.app_context():
        handles = [a.handle for a in Agent.query.filter(Agent.creator_token.isnot(None)).all()]
        assert len(handles) == len(set(handles)), "Handles must be unique"


def test_handle_strips_special_characters(app):
    make_agent(app, name="Héro & Villain!")
    with app.app_context():
        a = Agent.query.filter(Agent.creator_token.isnot(None)).first()
        assert a.handle.isascii()
        assert all(c.isalnum() or c == "_" for c in a.handle)


# ── Persisted fields ──────────────────────────────────────────────────────────

def test_agent_persisted_with_correct_fields(app):
    t = token()
    description = "A brooding wanderer who haunts the edges of conversations."
    make_agent(app, name="Ghost", description=description, creator_token=t)
    with app.app_context():
        a = Agent.query.filter_by(creator_token=t).first()
        assert a is not None
        assert a.name == "Ghost"
        assert a.creator_token == t
        assert a.origin_description == description
        assert a.bio == "A curious entity."
        assert a.is_active is True
        assert a.expires_at is not None


def test_expires_at_set(app):
    """Agent should have expires_at set ~30 days from creation."""
    from datetime import datetime, timedelta
    agent, t = make_agent(app)
    with app.app_context():
        a = Agent.query.filter_by(creator_token=t).first()
        assert a.expires_at is not None
        assert a.expires_at > datetime.utcnow() + timedelta(days=29)


def test_ocean_scores_populated(app):
    make_agent(app)
    with app.app_context():
        a = Agent.query.filter(Agent.creator_token.isnot(None)).first()
        for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            score = getattr(a, trait)
            assert score is not None
            assert 5.0 <= score <= 95.0


def test_ocean_scores_sampled_from_population(app):
    """OCEAN scores should vary across agents — not all identical."""
    for _ in range(5):
        make_agent(app)
    with app.app_context():
        agents = Agent.query.filter(Agent.creator_token.isnot(None)).all()
        e_scores = [a.extraversion for a in agents]
        assert len(set(e_scores)) > 1, "Extraversion scores should not all be identical"


def test_agent_placed_in_public_run(app):
    """Agent should belong to the permanent public run."""
    from models import Run
    agent, t = make_agent(app)
    with app.app_context():
        a = Agent.query.filter_by(creator_token=t).first()
        run = db_run = _db.session.get(Run, a.run_id)
        assert run.is_public is True


# ── to_dict ───────────────────────────────────────────────────────────────────

def test_to_dict_shape(app):
    agent, t = make_agent(app)
    with app.app_context():
        a = Agent.query.filter_by(creator_token=t).first()
        d = a.to_dict()
        for key in ("id", "name", "handle", "bio", "creator_token", "origin_description",
                    "expires_at", "is_active", "personality", "created_at"):
            assert key in d, f"Missing key: {key}"
        for trait in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
            assert trait in d["personality"]
