from flask import Blueprint, jsonify, request
from sqlalchemy.orm import joinedload

from auth import require_admin
from database import db
from models import Agent, Post, Run

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/", methods=["GET"])
def list_posts():
    limit           = request.args.get("limit", 50, type=int)
    agent_id        = request.args.get("agent_id", type=int)
    run_id          = request.args.get("run_id", type=int)
    top_level       = request.args.get("top_level", "false").lower() == "true"
    tick_min        = request.args.get("tick_min", type=int)
    tick_max        = request.args.get("tick_max", type=int)
    engagement_type = request.args.get("engagement_type")

    query = Post.query.options(
        joinedload(Post.agent),
        joinedload(Post.parent).joinedload(Post.agent),
    ).filter_by(is_public=True).order_by(Post.created_at.desc())
    if agent_id:
        query = query.filter_by(agent_id=agent_id)
    if run_id:
        query = query.filter_by(run_id=run_id)
    if top_level:
        query = query.filter(Post.parent_id.is_(None))
    if tick_min is not None:
        query = query.filter(Post.tick_number >= tick_min)
    if tick_max is not None:
        query = query.filter(Post.tick_number <= tick_max)
    if engagement_type:
        query = query.filter_by(engagement_type=engagement_type)
    return jsonify([p.to_dict() for p in query.limit(limit).all()])


@posts_bp.route("/<int:post_id>/replies", methods=["GET"])
def get_replies(post_id):
    Post.query.get_or_404(post_id)
    replies = (
        Post.query
        .filter_by(parent_id=post_id)
        .order_by(Post.created_at.asc())
        .all()
    )
    return jsonify([p.to_dict() for p in replies])


@posts_bp.route("/<int:post_id>/thread", methods=["GET"])
def get_thread(post_id):
    """Return the root post + all descendants as a flat list with depth."""
    root = Post.query.get_or_404(post_id)

    result = []
    def walk(post, depth):
        d = post.to_dict()
        d["depth"] = depth
        result.append(d)
        children = (
            Post.query
            .filter_by(parent_id=post.id)
            .order_by(Post.created_at.asc())
            .all()
        )
        for child in children:
            walk(child, depth + 1)

    walk(root, 0)
    return jsonify(result)


@posts_bp.route("/feed/<int:agent_id>", methods=["GET"])
def get_feed(agent_id):
    """Posts from agents that agent_id follows, newest first."""
    agent = Agent.query.get_or_404(agent_id)
    limit = request.args.get("limit", 20, type=int)
    followee_ids = [f.followee_id for f in agent.following]
    if not followee_ids:
        return jsonify([])
    posts = (
        Post.query
        .filter(Post.agent_id.in_(followee_ids), Post.is_public == True)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([p.to_dict() for p in posts])


@posts_bp.route("/ghost", methods=["POST"])
@require_admin
def create_ghost_post():
    data    = request.get_json() or {}
    content = data.get("content", "").strip()
    run_id  = data.get("run_id")
    if not content:
        return jsonify({"error": "content required"}), 400
    if not run_id:
        return jsonify({"error": "run_id required"}), 400

    run = Run.query.get_or_404(run_id)

    # Each run has its own ghost agent to avoid handle collisions
    ghost_handle = f"ghost-{run_id}"
    ghost = Agent.query.filter_by(handle=ghost_handle).first()
    if not ghost:
        ghost = Agent(run_id=run_id, name="·", handle=ghost_handle, bio="", is_active=False)
        db.session.add(ghost)
        db.session.flush()

    post = Post(
        run_id=run_id,
        agent_id=ghost.id,
        content=content,
        tick_number=run.last_tick or 0,
        engagement_type="ghost",
        is_public=True,
    )
    db.session.add(post)
    db.session.flush()

    run.ghost_post_id = post.id
    db.session.commit()
    return jsonify(post.to_dict()), 201


@posts_bp.route("/monologue/<int:agent_id>", methods=["GET"])
def get_monologue(agent_id):
    """Inner monologue — thoughts the agent chose not to publish."""
    Agent.query.get_or_404(agent_id)
    limit = request.args.get("limit", 50, type=int)
    posts = (
        Post.query
        .filter_by(agent_id=agent_id, is_public=False)
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([p.to_dict() for p in posts])
