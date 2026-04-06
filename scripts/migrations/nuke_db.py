"""Nuke all tables in prod. Run AFTER export_data.py."""
import psycopg2

DB = dict(
    host="dpg-d780cap5pdvs739h5u10-a.oregon-postgres.render.com",
    user="lurkr_db_user",
    password="gogUO0RhMX5CoyZJh9xnFClnKTK8vo8I",
    dbname="lurkr_db",
    port=5432,
)

TABLES = [
    "ipip_responses",
    "personality_snapshots",
    "follows",
    "posts",
    "news_items",
    "agents",
    "sim_state",
    "runs",
]

conn = psycopg2.connect(**DB)
conn.autocommit = True
cur = conn.cursor()

for table in TABLES:
    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    print(f"dropped {table}")

print("\nDone. Database is empty.")
conn.close()
