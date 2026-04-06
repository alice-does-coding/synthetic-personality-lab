"""
Export all prod data to JSON before nuking the database.
Run from backend/:  python export_data.py
"""

import json
import psycopg2
import psycopg2.extras
from datetime import datetime

DB = dict(
    host="dpg-d780cap5pdvs739h5u10-a.oregon-postgres.render.com",
    user="lurkr_db_user",
    password="gogUO0RhMX5CoyZJh9xnFClnKTK8vo8I",
    dbname="lurkr_db",
    port=5432,
)

TABLES = [
    "runs",
    "agents",
    "posts",
    "personality_snapshots",
    "ipip_responses",
    "news_items",
    "follows",
    "sim_state",
]

def export():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    out = {}
    for table in TABLES:
        cur.execute(f"SELECT * FROM {table}")
        rows = cur.fetchall()
        # Convert to plain dicts (RealDictRow isn't JSON serialisable directly)
        out[table] = [dict(r) for r in rows]
        print(f"  {table}: {len(rows)} rows")

    conn.close()

    filename = f"lurkr_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, "w") as f:
        json.dump(out, f, default=str, indent=2)

    print(f"\nExported to {filename}")
    return filename

if __name__ == "__main__":
    print("Exporting prod data...")
    export()
