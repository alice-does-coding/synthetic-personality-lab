from datetime import datetime
from database import db


class Run(db.Model):
    __tablename__ = "runs"

    id                = db.Column(db.Integer, primary_key=True)
    name              = db.Column(db.String(100), nullable=False)
    description       = db.Column(db.Text)
    model             = db.Column(db.String(100), nullable=False, default="mistral-large-latest")
    provider          = db.Column(db.String(50), nullable=False, default="mistral")
    model_version     = db.Column(db.String(100))
    news_enabled      = db.Column(db.Boolean, nullable=False, default=True)
    news_categories   = db.Column(db.JSON)  # list of category strings
    post_framing      = db.Column(db.Text)
    ipip_framing      = db.Column(db.Text)
    seed_distribution = db.Column(db.String(50), default="random")
    persona           = db.Column(db.String(50), nullable=True)   # null = random
    agent_count       = db.Column(db.Integer)
    tick_limit        = db.Column(db.Integer)
    tick_duration_s   = db.Column(db.Integer)
    batch_mode        = db.Column(db.Boolean, default=False, nullable=False)
    ipip_grounded     = db.Column(db.Boolean, default=True, nullable=False)
    random_seed       = db.Column(db.Integer, nullable=True)
    name_pool         = db.Column(db.JSON, nullable=True)  # list of names; overrides agent_count
    ghost_post_id     = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    status            = db.Column(db.String(20), nullable=False, default="pending")
    last_tick         = db.Column(db.Integer, default=0, nullable=False)
    # pending   — queued, seeding not started
    # seeding   — agents being generated in background
    # ready     — seeded, waiting in queue
    # running   — currently active
    # completed — hit tick_limit
    # stopped   — manually stopped
    # failed    — halted due to data quality failure (see error field)
    error             = db.Column(db.Text, nullable=True)
    started_at        = db.Column(db.DateTime)
    ended_at          = db.Column(db.DateTime)
    notes             = db.Column(db.Text)
    created_at        = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    agents             = db.relationship("Agent",               backref="run", lazy=True, cascade="all, delete-orphan")
    news_items         = db.relationship("NewsItem",            backref="run", lazy=True, cascade="all, delete-orphan")
    personality_snapshots = db.relationship("PersonalitySnapshot", backref="run", lazy=True, cascade="all, delete-orphan")
    ipip_responses     = db.relationship("IpipResponse",        backref="run", lazy=True, cascade="all, delete-orphan")
    events             = db.relationship("RunEvent",            backref="run", lazy=True, cascade="all, delete-orphan", order_by="RunEvent.id")

    def to_dict(self):
        return {
            "id":                self.id,
            "name":              self.name,
            "description":       self.description,
            "model":             self.model,
            "provider":          self.provider,
            "model_version":     self.model_version,
            "news_enabled":      self.news_enabled,
            "news_categories":   self.news_categories,
            "post_framing":      self.post_framing,
            "ipip_framing":      self.ipip_framing,
            "seed_distribution": self.seed_distribution,
            "persona":           self.persona,
            "agent_count":       self.agent_count,
            "tick_limit":        self.tick_limit,
            "tick_duration_s":   self.tick_duration_s,
            "batch_mode":        self.batch_mode,
            "ipip_grounded":     self.ipip_grounded,
            "random_seed":       self.random_seed,
            "name_pool":         self.name_pool,
            "ghost_post_id":     self.ghost_post_id,
            "status":            self.status,
            "last_tick":         self.last_tick,
            "error":             self.error,
            "started_at":        self.started_at.isoformat() if self.started_at else None,
            "ended_at":          self.ended_at.isoformat() if self.ended_at else None,
            "notes":             self.notes,
            "created_at":        self.created_at.isoformat(),
        }


class Agent(db.Model):
    __tablename__ = "agents"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    handle = db.Column(db.String(50), unique=True, nullable=False)
    bio = db.Column(db.Text, default="")
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    # Current Big Five scores (0–100), updated after each IPIP assessment
    openness = db.Column(db.Float, nullable=True)
    conscientiousness = db.Column(db.Float, nullable=True)
    extraversion = db.Column(db.Float, nullable=True)
    agreeableness = db.Column(db.Float, nullable=True)
    neuroticism = db.Column(db.Float, nullable=True)

    posts = db.relationship("Post", backref="agent", lazy=True, cascade="all, delete-orphan")
    snapshots = db.relationship("PersonalitySnapshot", backref="agent", lazy=True, cascade="all, delete-orphan")
    ipip_responses = db.relationship("IpipResponse", backref="agent", lazy=True, cascade="all, delete-orphan")

    following = db.relationship(
        "Follow",
        foreign_keys="Follow.follower_id",
        backref=db.backref("follower", lazy=True),
        lazy=True,
        cascade="all, delete-orphan",
    )
    followers = db.relationship(
        "Follow",
        foreign_keys="Follow.followee_id",
        backref=db.backref("followee", lazy=True),
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self, snapshot_count=None):
        return {
            "id": self.id,
            "name": self.name,
            "handle": self.handle,
            "bio": self.bio,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "personality": {
                "openness": self.openness,
                "conscientiousness": self.conscientiousness,
                "extraversion": self.extraversion,
                "agreeableness": self.agreeableness,
                "neuroticism": self.neuroticism,
            },
            "snapshot_count": snapshot_count if snapshot_count is not None else 0,
        }


class Post(db.Model):
    __tablename__ = "posts"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    content = db.Column(db.Text, nullable=False)
    tick_number = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    news_context = db.Column(db.JSON, nullable=True)  # headlines shown to agent when post was generated
    embedding = db.Column(db.JSON, nullable=True)
    engagement_type = db.Column(db.String(20), nullable=True)  # 'news', 'organic', 'reply'
    prompt = db.Column(db.Text, nullable=True)  # full user prompt sent to the LLM
    is_public = db.Column(db.Boolean, default=True, nullable=False)  # False = inner monologue
    sentiment = db.Column(db.Float, nullable=True)    # -1.0 → 1.0
    emotion = db.Column(db.String(50), nullable=True) # e.g. "joy", "sadness", "anger"
    nlp_analyzed = db.Column(db.Boolean, default=False, nullable=False)

    __table_args__ = (
        db.Index("ix_posts_run_id",            "run_id"),
        db.Index("ix_posts_agent_id",          "agent_id"),
        db.Index("ix_posts_run_created",       "run_id", "created_at"),
        db.Index("ix_posts_run_public",        "run_id", "is_public"),
        db.Index("ix_posts_run_nlp",           "run_id", "nlp_analyzed"),
        db.Index("ix_posts_news_context",      "run_id", postgresql_where=db.text("news_context IS NOT NULL")),
        db.Index("ix_posts_parent_id",         "parent_id"),
    )

    replies = db.relationship(
        "Post",
        backref=db.backref("parent", remote_side="Post.id"),
        lazy=True,
        cascade="all, delete-orphan",
    )

    def to_dict(self, reply_count=None):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_handle": self.agent.handle if self.agent else None,
            "agent_name": self.agent.name if self.agent else None,
            "content": self.content,
            "tick_number": self.tick_number,
            "created_at": self.created_at.isoformat(),
            "parent_id": self.parent_id,
            "parent_handle": self.parent.agent.handle if self.parent and self.parent.agent else None,
            "parent_content": self.parent.content if self.parent else None,
            "reply_count": reply_count if reply_count is not None else 0,
            "thread_count": reply_count if reply_count is not None else 0,
            "news_context": self.news_context,
            "engagement_type": self.engagement_type,
            "prompt": self.prompt,
            "is_public": self.is_public,
            "agent_openness": self.agent.openness if self.agent else None,
            "agent_conscientiousness": self.agent.conscientiousness if self.agent else None,
            "agent_extraversion": self.agent.extraversion if self.agent else None,
            "agent_agreeableness": self.agent.agreeableness if self.agent else None,
            "agent_neuroticism": self.agent.neuroticism if self.agent else None,
        }


class NewsItem(db.Model):
    """A unique headline seen by at least one agent, with semantic analysis."""
    __tablename__ = "news_items"

    id         = db.Column(db.Integer, primary_key=True)
    run_id     = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    url        = db.Column(db.String(500), nullable=False)
    title      = db.Column(db.Text, nullable=False)
    summary    = db.Column(db.Text, nullable=True)
    source     = db.Column(db.String(100))
    category   = db.Column(db.String(100))
    sentiment  = db.Column(db.Float,   nullable=True)   # -1.0 (negative) → 1.0 (positive)
    emotion    = db.Column(db.String(50), nullable=True) # e.g. "anxiety", "hope", "outrage"
    analyzed   = db.Column(db.Boolean, default=False, nullable=False)
    first_seen_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("run_id", "url", name="uq_news_item_run_url"),
    )

    def to_dict(self):
        return {
            "id":           self.id,
            "url":          self.url,
            "title":        self.title,
            "summary":      self.summary,
            "source":       self.source,
            "category":     self.category,
            "sentiment":    self.sentiment,
            "emotion":      self.emotion,
            "analyzed":     self.analyzed,
            "first_seen_at": self.first_seen_at.isoformat(),
        }


class Follow(db.Model):
    __tablename__ = "follows"

    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    followee_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("follower_id", "followee_id", name="uq_follow"),
    )


class PersonalitySnapshot(db.Model):
    """Time-series record of Big Five scores per agent per IPIP assessment."""
    __tablename__ = "personality_snapshots"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    tick_number = db.Column(db.Integer, nullable=False)
    openness = db.Column(db.Float, nullable=False)
    conscientiousness = db.Column(db.Float, nullable=False)
    extraversion = db.Column(db.Float, nullable=False)
    agreeableness = db.Column(db.Float, nullable=False)
    neuroticism = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_snapshots_run_id",        "run_id"),
        db.Index("ix_snapshots_agent_id",      "agent_id"),
        db.Index("ix_snapshots_run_tick",      "run_id", "tick_number"),
        db.Index("ix_snapshots_agent_tick",    "agent_id", "tick_number"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "tick_number": self.tick_number,
            "openness": self.openness,
            "conscientiousness": self.conscientiousness,
            "extraversion": self.extraversion,
            "agreeableness": self.agreeableness,
            "neuroticism": self.neuroticism,
            "created_at": self.created_at.isoformat(),
        }


class IpipResponse(db.Model):
    """Raw item-level responses from each IPIP-NEO-120 administration."""
    __tablename__ = "ipip_responses"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    agent_id = db.Column(db.Integer, db.ForeignKey("agents.id"), nullable=False)
    tick_number = db.Column(db.Integer, nullable=False)
    item_number = db.Column(db.Integer, nullable=False)  # 1–120
    score = db.Column(db.Integer, nullable=False)         # 1–5
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class RunEvent(db.Model):
    """Structured event log for a run — lifecycle, milestones, warnings, errors."""
    __tablename__ = "run_events"

    id         = db.Column(db.Integer, primary_key=True)
    run_id     = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=False)
    tick       = db.Column(db.Integer, nullable=True)
    level      = db.Column(db.String(10), nullable=False)   # info / warning / error
    message    = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    __table_args__ = (
        db.Index("ix_run_events_run_id", "run_id"),
    )

    def to_dict(self):
        return {
            "id":         self.id,
            "tick":       self.tick,
            "level":      self.level,
            "message":    self.message,
            "created_at": self.created_at.isoformat(),
        }


class SimState(db.Model):
    """Single-row table tracking global simulation state."""
    __tablename__ = "sim_state"

    id = db.Column(db.Integer, primary_key=True)
    run_id = db.Column(db.Integer, db.ForeignKey("runs.id"), nullable=True, default=None)
    current_tick = db.Column(db.Integer, default=0, nullable=False)
    is_running = db.Column(db.Boolean, default=False, nullable=False)
    ghost_post_id = db.Column(db.Integer, db.ForeignKey("posts.id"), nullable=True)
    updated_at = db.Column(
        db.DateTime,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    @classmethod
    def get(cls):
        state = cls.query.first()
        if state is None:
            state = cls(current_tick=0, is_running=False)
            db.session.add(state)
            db.session.commit()
        return state
