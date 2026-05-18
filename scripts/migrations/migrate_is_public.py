"""
Migration: complete the arcade → simulation rename in the database.

Two changes:
  1. Rename runs.is_arcade → runs.is_public. The flag distinguishes the
     permanent visitor-facing run from research runs, so `is_public` is more
     descriptive than the older product-branded name.
  2. Drop the empty `arcade_agents` table, left behind by the removed
     `ArcadeAgent` model. The class was declared but never instantiated, so
     any row count is zero in practice.

Idempotent — each step checks current schema state and is a no-op if already
applied.

  python migrate_is_public.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "")

CHECK_COLUMN_OLD = "SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='is_arcade'"
CHECK_COLUMN_NEW = "SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='is_public'"
CHECK_TABLE      = "SELECT 1 FROM information_schema.tables  WHERE table_name='arcade_agents'"
RENAME_COLUMN    = "ALTER TABLE runs RENAME COLUMN is_arcade TO is_public"
DROP_TABLE       = "DROP TABLE arcade_agents"


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


def _rename_is_arcade(cur):
    cur.execute(CHECK_COLUMN_NEW)
    if cur.fetchone():
        print("is_public already exists — skipping column rename.")
        return
    cur.execute(CHECK_COLUMN_OLD)
    if not cur.fetchone():
        print("Neither is_arcade nor is_public found on runs — schema is unexpected. Aborting.")
        raise RuntimeError("unexpected runs schema")
    cur.execute(RENAME_COLUMN)
    print("Renamed runs.is_arcade → runs.is_public.")


def _drop_arcade_agents(cur):
    cur.execute(CHECK_TABLE)
    if not cur.fetchone():
        print("arcade_agents table already gone — skipping drop.")
        return
    cur.execute(DROP_TABLE)
    print("Dropped arcade_agents table.")


def run():
    if not DB_URL:
        print("DATABASE_URL not set — aborting.")
        return
    print("Connecting...")
    conn = psycopg2.connect(**parse_url(DB_URL))
    conn.autocommit = False
    cur = conn.cursor()
    try:
        _rename_is_arcade(cur)
        _drop_arcade_agents(cur)
        conn.commit()
        print("Migration complete.")
    except Exception as e:
        conn.rollback()
        print(f"FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
