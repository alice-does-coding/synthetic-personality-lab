import pytest
from app import create_app
from database import db as _db
from models import Run, Agent, Follow


class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = "test-secret"
    ADMIN_KEY = "test-admin-key"
    MISTRAL_API_KEY = "fake-key"
    MISTRAL_MODEL = "mistral-large-latest"
    SIMULATION_TICK_SECONDS = 30
    FEED_SAMPLE_SIZE = 10
    AGENTS_PER_TICK = 5
    MAX_WORKERS = 1
    IPIP_WORKERS = 1
    REASSESSMENT_INTERVAL = 10
    MISTRAL_RATE_LIMIT = 1.0
    NLP_SERVICE_URL = "http://localhost:5001"
    HF_API_KEY = None
    N_THOUGHTS = 3
    MAX_POST_TOKENS = 300
    CORS_ORIGINS = "*"


@pytest.fixture(scope="session")
def app():
    return create_app(TestConfig)


@pytest.fixture(autouse=True)
def db(app):
    """Fresh in-memory database for every test."""
    with app.app_context():
        _db.create_all()
        yield _db
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin(app):
    """Test client with admin header pre-set."""
    c = app.test_client()
    c.environ_base["HTTP_X_ADMIN_KEY"] = "test-admin-key"
    return c


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_run(name="test-run", status="ready", **kwargs):
    run = Run(
        name=name,
        model="mistral-large-latest",
        news_enabled=True,
        post_framing="an entity on a social network",
        ipip_framing="your recent inner and outer life",
        seed_distribution="random",
        agent_count=5,
        tick_limit=100,
        status=status,
        **kwargs,
    )
    _db.session.add(run)
    _db.session.flush()
    return run


def make_agent(run_id, handle, **kwargs):
    agent = Agent(
        run_id=run_id,
        name=handle,
        handle=handle,
        bio="test bio",
        openness=50.0,
        conscientiousness=50.0,
        extraversion=50.0,
        agreeableness=50.0,
        neuroticism=50.0,
        **kwargs,
    )
    _db.session.add(agent)
    _db.session.flush()
    return agent
