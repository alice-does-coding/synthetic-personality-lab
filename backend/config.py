import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-change-me")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "sqlite:///lab.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY")
    MISTRAL_MODEL = os.getenv("MISTRAL_MODEL", "ministral-3b-latest")
    SIMULATION_TICK_SECONDS = int(os.getenv("SIMULATION_TICK_SECONDS", 10))
    FEED_SAMPLE_SIZE = int(os.getenv("FEED_SAMPLE_SIZE", 10))
    # Agents sampled per tick — keeps API calls manageable
    AGENTS_PER_TICK = int(os.getenv("AGENTS_PER_TICK", 25))
    # Concurrency for post generation
    MAX_WORKERS = int(os.getenv("MAX_WORKERS", 20))
    # Concurrency for IPIP assessments (lower — prompts are huge)
    IPIP_WORKERS = int(os.getenv("IPIP_WORKERS", 5))
    # Number of simulation ticks between full IPIP-NEO-120 re-assessments
    REASSESSMENT_INTERVAL = int(os.getenv("REASSESSMENT_INTERVAL", 10))
