from flask import Blueprint, jsonify
from sqlalchemy import func

from models import Agent, NewsItem, Post

news_bp = Blueprint("news", __name__)


@news_bp.route("/", methods=["GET"])
def list_news():
    """All tracked headlines, most-engaged first."""
    items = NewsItem.query.order_by(NewsItem.first_seen_at.desc()).all()

    # Count posts referencing each URL
    all_posts = Post.query.filter(Post.news_context.isnot(None)).all()
    engagement = {}
    for post in all_posts:
        for h in (post.news_context or []):
            url = h.get("url")
            if url:
                engagement[url] = engagement.get(url, 0) + 1

    result = []
    for item in items:
        d = item.to_dict()
        d["engagement"] = engagement.get(item.url, 0)
        result.append(d)

    result.sort(key=lambda x: x["engagement"], reverse=True)
    return jsonify(result)


@news_bp.route("/<int:item_id>/posts", methods=["GET"])
def news_posts(item_id):
    """Posts that were generated in response to this headline."""
    item = NewsItem.query.get_or_404(item_id)
    posts = Post.query.filter(Post.news_context.isnot(None)).all()
    matching = [
        p for p in posts
        if any(h.get("url") == item.url for h in (p.news_context or []))
    ]
    matching.sort(key=lambda p: p.created_at, reverse=True)
    return jsonify([p.to_dict() for p in matching])


@news_bp.route("/sentiment-over-time", methods=["GET"])
def sentiment_over_time():
    """Average sentiment of news injected per tick."""
    posts = Post.query.filter(Post.news_context.isnot(None)).order_by(Post.tick_number).all()

    # Build url→sentiment lookup
    items = {i.url: i.sentiment for i in NewsItem.query.filter_by(analyzed=True).all()}

    by_tick = {}
    for post in posts:
        for h in (post.news_context or []):
            url = h.get("url")
            if url and url in items and items[url] is not None:
                bucket = by_tick.setdefault(post.tick_number, [])
                bucket.append(items[url])

    result = [
        {"tick_number": tick, "avg_sentiment": sum(vals) / len(vals), "count": len(vals)}
        for tick, vals in sorted(by_tick.items())
    ]
    return jsonify(result)


@news_bp.route("/personality-correlation", methods=["GET"])
def personality_correlation():
    """For each agent: avg sentiment of news they engaged with + their OCEAN scores."""
    posts = Post.query.filter(Post.news_context.isnot(None)).all()
    items = {i.url: i.sentiment for i in NewsItem.query.filter_by(analyzed=True).all()}
    agents = {a.id: a for a in Agent.query.filter_by(is_active=True).all()}

    # Avg sentiment per agent
    agent_sentiments = {}
    for post in posts:
        sentiments = [
            items[h["url"]]
            for h in (post.news_context or [])
            if h.get("url") in items and items[h["url"]] is not None
        ]
        if sentiments:
            bucket = agent_sentiments.setdefault(post.agent_id, [])
            bucket.extend(sentiments)

    result = []
    for agent_id, sentiments in agent_sentiments.items():
        agent = agents.get(agent_id)
        if not agent or agent.openness is None:
            continue
        result.append({
            "agent_id":         agent_id,
            "agent_name":       agent.name,
            "agent_handle":     agent.handle,
            "avg_sentiment":    sum(sentiments) / len(sentiments),
            "engagement_count": len(sentiments),
            "openness":         agent.openness,
            "conscientiousness": agent.conscientiousness,
            "extraversion":     agent.extraversion,
            "agreeableness":    agent.agreeableness,
            "neuroticism":      agent.neuroticism,
        })

    return jsonify(result)
