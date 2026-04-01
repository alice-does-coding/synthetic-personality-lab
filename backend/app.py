from flask import Flask
from flask_cors import CORS
from apscheduler.schedulers.background import BackgroundScheduler

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

    app.register_blueprint(agents_bp, url_prefix="/api/agents")
    app.register_blueprint(posts_bp, url_prefix="/api/posts")
    app.register_blueprint(sim_bp, url_prefix="/api/sim")

    scheduler = BackgroundScheduler(daemon=True)

    def _tick():
        from simulation import run_tick
        run_tick(app)

    scheduler.add_job(
        func=_tick,
        trigger="interval",
        seconds=app.config["SIMULATION_TICK_SECONDS"],
        id="simulation_tick",
        replace_existing=True,
    )
    scheduler.start()
    app.scheduler = scheduler

    return app


if __name__ == "__main__":
    app = create_app()
    # use_reloader=False keeps APScheduler from spawning duplicate workers
    app.run(debug=True, use_reloader=False)
