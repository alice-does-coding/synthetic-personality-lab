import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    _db_url = os.getenv("DATABASE_URL", "sqlite:///lab.db")
    # Render provides postgres:// but SQLAlchemy requires postgresql://
    SQLALCHEMY_DATABASE_URI = _db_url.replace("postgres://", "postgresql://", 1)
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,       # verify connection before use — kills stale SSL sockets
        "pool_recycle":  300,        # recycle connections after 5 min regardless
    }
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "mistral-large-latest")
    SIMULATION_TICK_SECONDS = int(os.getenv("SIMULATION_TICK_SECONDS", 30))
    FEED_SAMPLE_SIZE = int(os.getenv("FEED_SAMPLE_SIZE", 10))
    # Agents sampled per tick — 0 means all agents
    AGENTS_PER_TICK = int(os.getenv("AGENTS_PER_TICK", 50))
    # Concurrency — match to Mistral rate limit
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 12))
    IPIP_WORKERS = int(os.getenv("IPIP_WORKERS", 12))
    # Number of simulation ticks between full IPIP-NEO-120 re-assessments
    REASSESSMENT_INTERVAL = int(os.getenv("REASSESSMENT_INTERVAL", 10))
    # Paid tier: 12 req/sec
    MISTRAL_RATE_LIMIT = float(os.getenv("MISTRAL_RATE_LIMIT", 12.0))
    # Local NLP microservice
    NLP_SERVICE_URL = os.getenv("NLP_SERVICE_URL", "http://localhost:5001")
    # Hugging Face Inference API key — enables news sentiment/emotion analysis
    HF_API_KEY = os.getenv("HF_API_KEY")
    # Thoughts generated per top-level post tick — 1 published, rest become inner monologue
    N_THOUGHTS = int(os.getenv("N_THOUGHTS", 3))
    # Max tokens per post/reply — increase if agents are getting cut off
    MAX_POST_TOKENS = int(os.getenv("MAX_POST_TOKENS", 60))  # ~140 chars
    # Admin key — required to call sim control and agent write endpoints
    ADMIN_KEY = os.getenv("ADMIN_KEY")
    # Restrict CORS in production — set to https://lurkr.net via env var
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
