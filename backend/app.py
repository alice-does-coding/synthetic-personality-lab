import threading
import time

from flask import Flask
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from config import Config
from database import db, init_db


def create_app(config_class=Config):
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
    from routes.nlp import nlp_bp
    from routes.runs import runs_bp

    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(sim_bp, url_prefix="/api/sim")
    app.register_blueprint(news_bp, url_prefix="/api/news")
    app.register_blueprint(nlp_bp, url_prefix="/api/nlp")
    app.register_blueprint(runs_bp, url_prefix="/api/runs")

    if not app.config.get("TESTING"):
        def _tick_loop():
            from simulation import run_tick
            while True:
                run_tick(app)
                interval = _tick_interval(app)
                if interval > 0:
                    time.sleep(interval)

        def _tick_interval(app):
            """Return 0 for batch runs so ticks chain back-to-back."""
            try:
                with app.app_context():
                    from models import Run, SimState
                    state = SimState.get()
                    if state.run_id:
                        run = db.session.get(Run, state.run_id)
                        if run and run.batch_mode:
                            return 0
            except Exception:
                pass
            return app.config["SIMULATION_TICK_SECONDS"]

        threading.Thread(target=_tick_loop, daemon=True).start()

        from simulation import start_news_analyzer, start_post_analyzer
        start_news_analyzer(app)
        start_post_analyzer(app)

    return app


if __name__ == "__main__":
    import os
    app = create_app()
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_ENV") != "production"
    app.run(debug=debug, use_reloader=False, host="0.0.0.0", port=port)
