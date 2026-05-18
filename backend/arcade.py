"""
Arcade agent generation service.

Creates user-submitted agents for the permanent public simulation (the Arcade).
Each pseudo-anon creator (UUID token stored client-side) gets one agent.
Agents are regular Agent rows — creator_token marks them as arcade-owned.

Seed modes
----------
describe  — user provides name + description; LLM writes the bio; OCEAN is sampled randomly.
random    — LLM generates name, bio, and OCEAN scores in one shot; no user input needed.
scratch   — user provides name, bio, and all five OCEAN values directly; no LLM involved.
"""
import json
import random
import re

from config import Config
from database import db
from llm import chat as llm_chat, extract_text as llm_extract_text
from models import Agent, Follow

MAX_AGENTS_PER_TOKEN = 1

_POPULATION_NORMS = {
    "openness":          (60, 20),
    "conscientiousness": (55, 20),
    "extraversion":      (50, 22),
    "agreeableness":     (62, 18),
    "neuroticism":       (45, 22),
}

FOLLOWS_PER_ARCADE_AGENT = 5
_OCEAN_TRAITS = ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism")


def _sample_score(mean, std):
    return round(max(5.0, min(95.0, random.gauss(mean, std))), 1)


def _sample_ocean():
    return {k: _sample_score(*v) for k, v in _POPULATION_NORMS.items()}


def _pick_follow_targets(new_interests, candidates, n):
    """
    Pick n follow targets weighted by interest compatibility.
    Top-compatible agents are more likely to be chosen, but there's still
    randomness so the graph doesn't become perfectly clustered.
    Falls back to random sample if candidates is small or interests are empty.
    """
    from interests import interest_compatibility
    if not candidates:
        return []
    if len(candidates) <= n:
        return candidates

    if not new_interests:
        return random.sample(candidates, n)

    # Score each candidate and use scores as sampling weights
    weights = [
        interest_compatibility(new_interests, c.interests or []) + 0.05  # +epsilon so zeros still eligible
        for c in candidates
    ]
    # Weighted sample without replacement
    chosen, pool, w = [], list(candidates), list(weights)
    for _ in range(n):
        total = sum(w)
        r = random.random() * total
        cumulative = 0.0
        for i, wi in enumerate(w):
            cumulative += wi
            if r <= cumulative:
                chosen.append(pool.pop(i))
                w.pop(i)
                break
    return chosen


def _should_follow_back(existing_agent, new_agent):
    """Probabilistic follow-back on join. High A + high E = warm, reciprocal. High N = selective."""
    A = (existing_agent.agreeableness or 62.0) / 100.0
    E = (existing_agent.extraversion  or 50.0) / 100.0
    N = (existing_agent.neuroticism   or 45.0) / 100.0
    p = 0.15 + (A * 0.40) + (E * 0.25) - (N * 0.20)
    return random.random() < max(0.05, min(0.90, p))


def _make_handle(name, existing_handles):
    base = re.sub(r"[^a-z0-9_]", "", name.lower().replace(" ", "_"))[:28] or "agent"
    handle = base
    i = 2
    while handle in existing_handles:
        handle = f"{base}{i}"
        i += 1
    return handle


# ── Seed mode: describe ───────────────────────────────────────────────────────

def _generate_bio(name, description, provider=None, model=None):
    """Generate a bio from a user-written description."""
    provider = provider or "mistral"
    model = model or Config.MISTRAL_POST_MODEL

    prompt = (
        f"Write a bio for an entity named {name}.\n"
        f"Character description provided by their creator: {description}\n\n"
        "Rules: exactly 1-2 sentences, first person, capture the essence of the description, "
        "no markdown, no options, no commentary.\n\n"
        "Return JSON only:\n"
        '{"bio": "..."}'
    )

    messages = [{"role": "user", "content": prompt}]
    resp = llm_chat(provider, model, messages, 150, 1.0)
    raw_content = resp.choices[0].message.content if hasattr(resp, "choices") else resp
    raw = llm_extract_text(provider, raw_content).strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")
    data = json.loads(raw)
    return data["bio"].strip().strip('"')


# ── Seed mode: random ─────────────────────────────────────────────────────────

def _generate_random_agent(provider=None, model=None):
    """
    Ask the LLM to invent a complete agent — name, bio, and OCEAN scores.
    Returns (name: str, bio: str, ocean: dict).
    """
    provider = provider or "mistral"
    model = model or Config.MISTRAL_POST_MODEL

    prompt = (
        "Generate a fictional social media user with a distinct, specific personality.\n\n"
        "Rules:\n"
        "- Diverse demographics: any gender, age, culture, background\n"
        "- Interesting, non-generic personality — avoid archetypes like 'tech bro' or 'soccer mom'\n"
        "- Bio: exactly 1-2 sentences, first person, voice matches the personality\n"
        "- OCEAN scores: integers 0-100 that honestly reflect the personality\n"
        "- Name: realistic, culturally varied — not always Western\n\n"
        "Return JSON only:\n"
        '{"name": "...", "bio": "...", "openness": 0, "conscientiousness": 0, '
        '"extraversion": 0, "agreeableness": 0, "neuroticism": 0}'
    )
    messages = [{"role": "user", "content": prompt}]
    resp = llm_chat(provider, model, messages, 200, 1.1)
    raw_content = resp.choices[0].message.content if hasattr(resp, "choices") else resp
    raw = llm_extract_text(provider, raw_content).strip()
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")
    data = json.loads(raw)

    name = str(data["name"]).strip()[:50]
    bio  = str(data["bio"]).strip()
    ocean = {
        t: round(max(5.0, min(95.0, float(data[t]))), 1)
        for t in _OCEAN_TRAITS
    }
    return name, bio, ocean


# ── Seed mode: scratch ────────────────────────────────────────────────────────

def _validate_scratch(name, bio, scores):
    """Validate scratch-mode inputs. Raises ValueError on failure."""
    if not name or len(name) > 50:
        raise ValueError("Name must be 1–50 characters.")
    if not bio or len(bio) > 1000:
        raise ValueError("Bio must be 1–1000 characters.")
    for trait in _OCEAN_TRAITS:
        if trait not in scores:
            raise ValueError(f"Missing OCEAN score: {trait}.")
        v = scores[trait]
        if not isinstance(v, (int, float)) or not (0 <= v <= 100):
            raise ValueError(f"{trait} must be a number between 0 and 100.")


# ── Public API ────────────────────────────────────────────────────────────────

def create_arcade_agent(
    creator_token,
    seed_mode="describe",
    *,
    # describe mode
    name=None,
    description=None,
    # scratch mode
    bio=None,
    openness=None,
    conscientiousness=None,
    extraversion=None,
    agreeableness=None,
    neuroticism=None,
    # shared
    provider=None,
    model=None,
):
    """
    Generate and persist a new arcade agent into the permanent arcade run.

    seed_mode="describe"  — name + description required; bio via LLM; OCEAN sampled.
    seed_mode="random"    — everything generated by LLM; no extra fields needed.
    seed_mode="scratch"   — name, bio, and all five OCEAN values required; no LLM.

    Returns the Agent on success.
    Raises ValueError for validation failures.
    """
    from arcade_run import get_or_create_arcade_run, ARCADE_AGENT_LIFETIME_DAYS
    from datetime import datetime, timedelta
    from flask import current_app

    if not creator_token:
        raise ValueError("creator_token is required.")

    existing = Agent.query.filter_by(creator_token=creator_token).count()
    if existing >= MAX_AGENTS_PER_TOKEN:
        raise ValueError("You already have an agent in the arcade.")

    # ── Resolve name, bio, ocean per seed mode ────────────────────────────────
    if seed_mode == "random":
        name, bio, scores = _generate_random_agent(provider, model)
        origin_description = None

    elif seed_mode == "scratch":
        name = (name or "").strip()
        bio  = (bio  or "").strip()
        scores = {
            "openness":          openness,
            "conscientiousness": conscientiousness,
            "extraversion":      extraversion,
            "agreeableness":     agreeableness,
            "neuroticism":       neuroticism,
        }
        _validate_scratch(name, bio, scores)
        scores = {t: round(float(scores[t]), 1) for t in _OCEAN_TRAITS}
        origin_description = None

    else:  # describe (default)
        name        = (name        or "").strip()
        description = (description or "").strip()
        if not name or len(name) > 50:
            raise ValueError("Name must be 1–50 characters.")
        if len(description) < 10 or len(description) > 500:
            raise ValueError("Description must be 10–500 characters.")
        bio    = _generate_bio(name, description, provider, model)
        scores = _sample_ocean()
        origin_description = description

    # ── Persist ───────────────────────────────────────────────────────────────
    run_id = get_or_create_arcade_run(current_app._get_current_object())

    existing_handles = {a.handle for a in Agent.query.with_entities(Agent.handle).all()}
    handle = _make_handle(name, existing_handles)

    from interests import compute_interests
    agent_interests = compute_interests(
        scores["openness"], scores["conscientiousness"], scores["extraversion"],
        scores["agreeableness"], scores["neuroticism"],
    )

    agent = Agent(
        run_id=run_id,
        name=name,
        handle=handle,
        bio=bio,
        creator_token=creator_token,
        origin_description=origin_description,
        expires_at=datetime.utcnow() + timedelta(days=ARCADE_AGENT_LIFETIME_DAYS),
        openness=scores["openness"],
        conscientiousness=scores["conscientiousness"],
        extraversion=scores["extraversion"],
        agreeableness=scores["agreeableness"],
        neuroticism=scores["neuroticism"],
        interests=agent_interests,
    )
    db.session.add(agent)
    db.session.flush()

    # Generate avatar via FLUX — best-effort, never blocks agent creation
    try:
        from llm import generate_avatar
        avatar = generate_avatar("hf", bio, name=name)
        if avatar:
            agent.avatar = avatar
    except Exception:
        pass

    # Wire into the social graph — follow agents with compatible interests
    arcade_agents = (
        Agent.query
        .filter_by(run_id=run_id, is_active=True)
        .filter(Agent.id != agent.id)
        .all()
    )
    targets = _pick_follow_targets(agent_interests, arcade_agents, FOLLOWS_PER_ARCADE_AGENT)
    for target in targets:
        db.session.add(Follow(follower_id=agent.id, followee_id=target.id))
        # Existing agent follows back based on their personality
        if _should_follow_back(target, agent):
            db.session.add(Follow(follower_id=target.id, followee_id=agent.id))

    db.session.commit()

    # New agent gets an intro post in a background thread
    import threading as _threading
    from models import Run as _Run
    _run       = db.session.get(_Run, run_id)
    _flask_app = current_app._get_current_object()
    _agent_id  = agent.id
    _run_id    = run_id
    _provider  = _run.provider
    _model     = _run.model
    _tick      = (_run.last_tick or 0) + 1

    def _do_intro():
        from simulation import generate_intro_post
        generate_intro_post(_flask_app, _agent_id, _run_id, _tick, _provider, _model)

    _threading.Thread(target=_do_intro, daemon=True).start()

    return agent
