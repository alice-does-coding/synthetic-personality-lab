"""
Migration: rename runs.is_arcade → runs.is_public.

Part of the arcade → simulation rename. The flag distinguishes the permanent
visitor-facing run from research runs, so `is_public` is more descriptive than
the older product-branded name.

Safe to run multiple times — checks for column existence before each step
and is a no-op if the migration has already been applied.

  python migrate_is_public.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "")

CHECK_OLD = "SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='is_arcade'"
CHECK_NEW = "SELECT 1 FROM information_schema.columns WHERE table_name='runs' AND column_name='is_public'"
RENAME    = "ALTER TABLE runs RENAME COLUMN is_arcade TO is_public"


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
        cur.execute(CHECK_NEW)
        if cur.fetchone():
            print("is_public already exists — nothing to do.")
            return
        cur.execute(CHECK_OLD)
        if not cur.fetchone():
            print("Neither is_arcade nor is_public found on runs — schema is unexpected. Aborting.")
            return
        cur.execute(RENAME)
        conn.commit()
        print("Renamed runs.is_arcade → runs.is_public.")
    except Exception as e:
        conn.rollback()
        print(f"FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
