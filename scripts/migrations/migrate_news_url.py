"""
Migration: fix news_items URL uniqueness constraint.

The original schema had url as globally unique, which prevents the same
headline URL from appearing in more than one run. This crashes tick 1 of
any new run when current headlines were already seen in a previous run.

Changes:
  - DROP unique constraint on news_items.url
  - ADD unique constraint on (run_id, url)

Safe to run multiple times (uses IF EXISTS / IF NOT EXISTS).

Run with:
  python migrate_news_url.py
"""

import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is required.")

MIGRATION = """
-- Drop the global unique constraint on url
ALTER TABLE news_items DROP CONSTRAINT IF EXISTS news_items_url_key;

-- Add per-run unique constraint: same URL can appear in multiple runs
ALTER TABLE news_items
    ADD CONSTRAINT uq_news_item_run_url UNIQUE (run_id, url);
"""

def run():
    print("Connecting to DB...")
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Running migration...")
        cur.execute(MIGRATION)
        conn.commit()
        print("Migration complete.")

        cur.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints
            WHERE table_name = 'news_items'
        """)
        constraints = cur.fetchall()
        print("\nnews_items constraints:")
        for c in constraints:
            print(f"  {c[0]} ({c[1]})")

    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
