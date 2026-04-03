from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def _add_columns_if_missing(engine):
    """Safely add new columns to existing SQLite tables without a full migration."""
    new_columns = [
        ("posts", "engagement_type", "VARCHAR(20)"),
        ("posts", "prompt",          "TEXT"),
    ]
    with engine.connect() as conn:
        for table, column, col_type in new_columns:
            try:
                conn.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}"))
                conn.commit()
            except Exception:
                pass  # column already exists


def init_db(app):
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        import models  # noqa: F401 — ensures all models are registered before create_all
        db.create_all()
        _add_columns_if_missing(db.engine)
