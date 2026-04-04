from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

db = SQLAlchemy()
migrate = Migrate()


def init_db(app):
    db.init_app(app)
    migrate.init_app(app, db)
    with app.app_context():
        import models  # noqa: F401 — ensures all models are registered before create_all
        db.create_all()
