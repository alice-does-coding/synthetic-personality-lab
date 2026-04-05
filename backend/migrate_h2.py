"""
Migration: add H2 experiment fields to runs table.

Adds:
  - ipip_grounded  BOOLEAN NOT NULL DEFAULT TRUE
    Controls whether agents see their recent posts before IPIP self-assessment.
    True = grounded condition (behavioral evidence shown).
    False = ungrounded control (no post history — tests H2).

  - random_seed    INTEGER NULL
    When set, seeds the Python RNG at seeding time for reproducible
    agent populations. Two runs with the same random_seed and config
    will produce identical agents, social graphs, and initial scores.
    Enables matched-pairs experimental design.

Run with:
  python migrate_h2.py
"""

import psycopg2

DB = dict(
    host="dpg-d780cap5pdvs739h5u10-a.oregon-postgres.render.com",
    user="lurkr_db_user",
    password="gogUO0RhMX5CoyZJh9xnFClnKTK8vo8I",
    dbname="lurkr_db",
    port=5432,
)

MIGRATION = """
ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS ipip_grounded BOOLEAN NOT NULL DEFAULT TRUE;

ALTER TABLE runs
    ADD COLUMN IF NOT EXISTS random_seed INTEGER;
"""

def run():
    print("Connecting to prod DB...")
    conn = psycopg2.connect(**DB)
    conn.autocommit = False
    cur = conn.cursor()

    try:
        print("Running migration...")
        cur.execute(MIGRATION)
        conn.commit()
        print("Migration complete.")

        cur.execute("SELECT id, name, ipip_grounded, random_seed FROM runs ORDER BY id")
        runs = cur.fetchall()
        print(f"\nRuns table ({len(runs)} row(s)):")
        for r in runs:
            print(f"  id={r[0]} name={r[1]} ipip_grounded={r[2]} random_seed={r[3]}")

    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
