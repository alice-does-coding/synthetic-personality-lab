"""
Add performance indexes to posts and personality_snapshots.

Run once against prod:
    python migrate_indexes.py

Uses CREATE INDEX CONCURRENTLY so it doesn't lock the tables.
Safe to run while the simulation is active.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("DATABASE_URL", "")
if len(sys.argv) > 1:
    url = sys.argv[1]

if not url or url.startswith("sqlite"):
    print("Usage: python migrate_indexes.py <postgres_database_url>")
    print("  or set DATABASE_URL env var to a postgres:// URL")
    sys.exit(1)

DATABASE_URL = url.replace("postgres://", "postgresql://", 1)

INDEXES = [
    ("ix_posts_run_id",       "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_run_id ON posts (run_id)"),
    ("ix_posts_agent_id",     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_agent_id ON posts (agent_id)"),
    ("ix_posts_run_created",  "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_run_created ON posts (run_id, created_at DESC)"),
    ("ix_posts_run_public",   "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_run_public ON posts (run_id, is_public)"),
    ("ix_posts_run_nlp",      "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_run_nlp ON posts (run_id, nlp_analyzed)"),
    ("ix_posts_news_context", "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_posts_news_context ON posts (run_id) WHERE news_context IS NOT NULL"),
    ("ix_snaps_run_id",       "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_snaps_run_id ON personality_snapshots (run_id)"),
    ("ix_snaps_agent_id",     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_snaps_agent_id ON personality_snapshots (agent_id)"),
    ("ix_snaps_run_tick",     "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_snaps_run_tick ON personality_snapshots (run_id, tick_number)"),
    ("ix_snaps_agent_tick",   "CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_snaps_agent_tick ON personality_snapshots (agent_id, tick_number)"),
]

def main():
    # CONCURRENTLY requires autocommit
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = True
    cur = conn.cursor()

    for name, sql in INDEXES:
        print(f"  creating {name}...", end=" ", flush=True)
        try:
            cur.execute(sql)
            print("done")
        except Exception as e:
            print(f"skipped ({e})")

    cur.close()
    conn.close()
    print("\nAll done.")

if __name__ == "__main__":
    main()
