"""
Migration: complete the arcade → simulation rename in the database.

Three changes, all idempotent:
  1. Rename runs.is_arcade → runs.is_public. Handles three states:
       - only is_arcade exists  → RENAME
       - both exist             → copy values from is_arcade to is_public, drop is_arcade
       - only is_public exists  → no-op
  2. Rename the public-run row: name '__arcade__' → '__simulation__'.
  3. Drop the empty `arcade_agents` table left behind by the removed
     `ArcadeAgent` model.

The same logic also runs automatically inside backend/database.py on every
app boot, so this script is mainly here for researchers who want to apply
the schema fix without a full deploy.

  python migrate_is_public.py
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL", "")


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


def _has_column(cur, table, column):
    cur.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name=%s AND column_name=%s",
        (table, column),
    )
    return cur.fetchone() is not None


def _has_table(cur, table):
    cur.execute(
        "SELECT 1 FROM information_schema.tables WHERE table_name=%s",
        (table,),
    )
    return cur.fetchone() is not None


def _migrate_is_arcade(cur):
    has_old = _has_column(cur, "runs", "is_arcade")
    has_new = _has_column(cur, "runs", "is_public")
    if has_old and not has_new:
        cur.execute("ALTER TABLE runs RENAME COLUMN is_arcade TO is_public")
        print("Renamed runs.is_arcade → runs.is_public.")
    elif has_old and has_new:
        cur.execute("UPDATE runs SET is_public = is_arcade WHERE is_arcade IS TRUE")
        cur.execute("ALTER TABLE runs DROP COLUMN is_arcade")
        print("Both columns existed — copied is_arcade values into is_public, dropped is_arcade.")
    else:
        print("is_arcade column already gone — skipping.")


def _rename_run_row(cur):
    cur.execute("UPDATE runs SET name='__simulation__' WHERE name='__arcade__'")
    if cur.rowcount:
        print(f"Renamed {cur.rowcount} run row(s): __arcade__ → __simulation__.")
    else:
        print("No __arcade__ run row to rename.")


def _drop_arcade_agents(cur):
    if not _has_table(cur, "arcade_agents"):
        print("arcade_agents table already gone — skipping drop.")
        return
    cur.execute("DROP TABLE arcade_agents")
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
        _migrate_is_arcade(cur)
        _rename_run_row(cur)
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
