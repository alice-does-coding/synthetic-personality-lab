"""
Migration: add multi-run support.

Creates:
  - runs table (experiment control variables)

Adds run_id to:
  - agents, posts, personality_snapshots, ipip_responses, news_items, sim_state

Backfills existing data as run_id = 1 (the original 957-tick Mistral run).

Safe to inspect before running. Run with:
  python migrate_runs.py
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
-- 1. Create runs table
CREATE TABLE IF NOT EXISTS runs (
    id                SERIAL PRIMARY KEY,
    name              VARCHAR(100) NOT NULL,
    description       TEXT,
    model             VARCHAR(100) NOT NULL DEFAULT 'mistral-large-latest',
    model_version     VARCHAR(100),
    news_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    news_categories   TEXT[],
    post_framing      TEXT,
    ipip_framing      TEXT,
    seed_distribution VARCHAR(50) DEFAULT 'random',
    agent_count       INTEGER,
    tick_limit        INTEGER,
    tick_duration_s   INTEGER,
    started_at        TIMESTAMP,
    ended_at          TIMESTAMP,
    notes             TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW()
);

-- 2. Insert run 1 — the original Mistral run
INSERT INTO runs (
    id, name, description, model, news_enabled,
    post_framing, ipip_framing, seed_distribution, agent_count,
    tick_limit, tick_duration_s, notes, started_at, ended_at
)
VALUES (
    1,
    'baseline-mistral-news',
    'Original run. Mistral-large-latest, news enabled (all categories), no framing. 30 agents, 957 ticks.',
    'mistral-large-latest',
    TRUE,
    'a user on a social media platform',
    'your recent inner and outer life',
    'random',
    30,
    957,
    30,
    'First run. Discovered neuroticism attractor (60-80 basin), financial-existential vocabulary, Patrick Bateman prior. Ghost post perturbation experiment conducted ~tick 320. New agent cohort injected mid-run.',
    '2026-04-01',
    '2026-04-04'
)
ON CONFLICT (id) DO NOTHING;

-- 3. Add run_id columns (nullable first so existing rows are not rejected)
ALTER TABLE agents
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

ALTER TABLE posts
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

ALTER TABLE personality_snapshots
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

ALTER TABLE ipip_responses
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

ALTER TABLE news_items
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

ALTER TABLE sim_state
    ADD COLUMN IF NOT EXISTS run_id INTEGER REFERENCES runs(id);

-- 4. Backfill all existing rows to run 1
UPDATE agents               SET run_id = 1 WHERE run_id IS NULL;
UPDATE posts                SET run_id = 1 WHERE run_id IS NULL;
UPDATE personality_snapshots SET run_id = 1 WHERE run_id IS NULL;
UPDATE ipip_responses        SET run_id = 1 WHERE run_id IS NULL;
UPDATE news_items            SET run_id = 1 WHERE run_id IS NULL;
UPDATE sim_state             SET run_id = 1 WHERE run_id IS NULL;

-- 5. Now make run_id NOT NULL
ALTER TABLE agents                ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE posts                 ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE personality_snapshots ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE ipip_responses        ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE news_items            ALTER COLUMN run_id SET NOT NULL;
ALTER TABLE sim_state             ALTER COLUMN run_id SET NOT NULL;
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

        # Verify
        cur.execute("SELECT id, name, model, news_enabled, tick_limit FROM runs ORDER BY id")
        runs = cur.fetchall()
        print(f"\nRuns table ({len(runs)} row(s)):")
        for r in runs:
            print(f"  id={r[0]} name={r[1]} model={r[2]} news={r[3]} tick_limit={r[4]}")

        for table in ["agents", "posts", "personality_snapshots", "ipip_responses", "news_items"]:
            cur.execute(f"SELECT COUNT(*) FROM {table} WHERE run_id = 1")
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows backfilled to run_id=1")

    except Exception as e:
        conn.rollback()
        print(f"Migration FAILED — rolled back: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    run()
