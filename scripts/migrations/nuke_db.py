"""
Nuke all tables in the target database. Reads DATABASE_URL from the environment.

Usage:
  DATABASE_URL=postgres://... python nuke_db.py
"""
import os
import sys
import psycopg2

DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    sys.exit("DATABASE_URL is required. Refusing to run with no target.")

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

conn = psycopg2.connect(DATABASE_URL)
conn.autocommit = True
cur = conn.cursor()

for table in TABLES:
    cur.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
    print(f"dropped {table}")

print("\nDone. Database is empty.")
conn.close()
