"""
Migration: add batch_mode + persona + status to runs table.

Safe to run multiple times (uses IF NOT EXISTS / ADD COLUMN IF NOT EXISTS).

  python migrate_batch_mode.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "")

MIGRATION = """
ALTER TABLE runs ADD COLUMN IF NOT EXISTS batch_mode BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE runs ADD COLUMN IF NOT EXISTS persona VARCHAR(50);
ALTER TABLE runs ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT 'completed';
ALTER TABLE runs ADD COLUMN IF NOT EXISTS last_tick INTEGER NOT NULL DEFAULT 0;
"""

def parse_url(url):
    """Parse postgres://user:pass@host:port/dbname into psycopg2 kwargs."""
    url = url.replace("postgres://", "").replace("postgresql://", "")
    userpass, rest = url.split("@", 1)
    user, password = userpass.split(":", 1)
    hostport, dbname = rest.split("/", 1)
    if ":" in hostport:
        host, port = hostport.split(":", 1)
    else:
        host, port = hostport, "5432"
    return dict(host=host, user=user, password=password, dbname=dbname, port=int(port))


def run():
    if not DB_URL:
        print("DATABASE_URL not set — aborting.")
        return
    print("Connecting...")
    conn = psycopg2.connect(**parse_url(DB_URL))
    conn.autocommit = False
    cur = conn.cursor()
    try:
        cur.execute(MIGRATION)
        conn.commit()
        print("Migration complete.")
        cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='runs' ORDER BY ordinal_position")
        print("runs columns:", [r[0] for r in cur.fetchall()])
    except Exception as e:
        conn.rollback()
        print(f"FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
