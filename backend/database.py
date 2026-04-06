from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()

# Columns added after initial deploy — applied automatically on startup.
# Safe to re-run: IF NOT EXISTS / try-except handles idempotency.
_MIGRATIONS = [
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS error TEXT",
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS provider VARCHAR(50) NOT NULL DEFAULT 'mistral'",
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS avatar TEXT",
]


def _run_migrations():
    import logging
    log = logging.getLogger(__name__)
    for sql in _MIGRATIONS:
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
