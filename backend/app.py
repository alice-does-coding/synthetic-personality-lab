import logging
import threading

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from database import db, init_db


def create_app(config_class=Config):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    app = Flask(__name__)
    app.config.from_object(config_class)

    origins = app.config.get("CORS_ORIGINS", "*")
    CORS(app, origins=origins)

    Limiter(
        get_remote_address,
        app=app,
        default_limits=["120 per minute"],
        storage_uri="memory://",
    )

    init_db(app)

    from routes.agents import agents_bp
    from routes.posts import posts_bp
    from routes.sim import sim_bp
    from routes.news import news_bp
    from routes.runs import runs_bp

    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(sim_bp, url_prefix="/api/sim")
    app.register_blueprint(news_bp, url_prefix="/api/news")
    app.register_blueprint(runs_bp, url_prefix="/api/runs")

    if not app.config.get("TESTING"):
        # Resume any research runs that were mid-flight when the process last stopped.
        # Set NO_RESUME=1 to skip (e.g. make report, CI, fresh snapshots).
        import os as _os
        if not _os.environ.get("NO_RESUME"):
            def _resume_running_runs():
                from engine import start_run_thread
                from models import Run
                with app.app_context():
                    running = Run.query.filter_by(status="running").all()
                    for run in running:
                        start_run_thread(app, run.id)

            threading.Thread(target=_resume_running_runs, daemon=True).start()

        from nlp_analyzer import start_news_analyzer, start_post_analyzer
        start_news_analyzer(app)
        start_post_analyzer(app)

    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug, use_reloader=False, host="0.0.0.0", port=port)
