from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

# Columns added after initial deploy — applied automatically on startup.
# Safe to re-run: IF NOT EXISTS / try-except handles idempotency.
# Each entry: (postgres_sql, sqlite_sql) — use None for sqlite_sql to share the same statement.
# SQLite doesn't support IF NOT EXISTS on ALTER TABLE ADD COLUMN, so we list the bare form
# and rely on the "duplicate column" / "already exists" guard in the except block.
_MIGRATIONS = [
    (
        "ALTER TABLE runs ADD COLUMN IF NOT EXISTS error TEXT",
        "ALTER TABLE runs ADD COLUMN error TEXT",
    ),
]


def _run_migrations():
    import logging
    log = logging.getLogger(__name__)
    is_sqlite = "sqlite" in str(db.engine.url)
    for pg_sql, sqlite_sql in _MIGRATIONS:
        sql = sqlite_sql if is_sqlite else pg_sql
        try:
            db.session.execute(db.text(sql))
            db.session.commit()
            log.info("migration ok: %s", sql[:60])
        except Exception as exc:
            db.session.rollback()
            msg = str(exc).lower()
            if "duplicate column" not in msg and "already exists" not in msg:
                log.warning("migration skipped (%s): %s", type(exc).__name__, sql[:60])


def init_db(app):
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        import models  # noqa: F401 — ensures all models are registered before create_all
        db.create_all()
        _run_migrations()
