from flask import Blueprint, jsonify, request

from models import Agent, Post

posts_bp = Blueprint("posts", __name__)


@posts_bp.route("/", methods=["GET"])
def list_posts():
    limit    = request.args.get("limit", 50, type=int)
    agent_id = request.args.get("agent_id", type=int)
    query = Post.query.order_by(Post.created_at.desc())
    if agent_id:
        query = query.filter_by(agent_id=agent_id)
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
        .filter(Post.agent_id.in_(followee_ids))
        .order_by(Post.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify([p.to_dict() for p in posts])
