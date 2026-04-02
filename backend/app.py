import threading
import time

from flask import Flask
from flask_cors import CORS

from config import Config
from database import init_db


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    CORS(app)
    init_db(app)

    from routes.agents import agents_bp
    from routes.posts import posts_bp
    from routes.sim import sim_bp
    from routes.news import news_bp
    from routes.nlp import nlp_bp

    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(sim_bp, url_prefix="/api/sim")
    app.register_blueprint(news_bp, url_prefix="/api/news")
    app.register_blueprint(nlp_bp, url_prefix="/api/nlp")

    def _tick_loop():
        from simulation import run_tick
        while True:
            run_tick(app)
            time.sleep(app.config["SIMULATION_TICK_SECONDS"])

    threading.Thread(target=_tick_loop, daemon=True).start()

    from simulation import start_news_analyzer
    start_news_analyzer(app)

    return app


if __name__ == "__main__":
    app = create_app()
    # use_reloader=False keeps APScheduler from spawning duplicate workers
    app.run(debug=True, use_reloader=False)
