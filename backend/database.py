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
    # 2026-04-06 — behavior model + public simulation
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS behavior_model VARCHAR(50)",
    "ALTER TABLE runs ADD COLUMN IF NOT EXISTS is_public BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS creator_token VARCHAR(36)",
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS origin_description TEXT",
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS expires_at_tick INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_agents_creator_token ON agents (creator_token)",
    # 2026-04-07 — interest model
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS interests JSONB",
    "ALTER TABLE posts ADD COLUMN IF NOT EXISTS topics JSONB",
    # 2026-04-07 — decouple lifetime from tick count; use wall-clock expiry
    "ALTER TABLE agents ADD COLUMN IF NOT EXISTS expires_at TIMESTAMP",
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
