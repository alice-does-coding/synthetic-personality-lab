"""
Seed the database with agents with fully randomised Big Five scores.
Identity (name, handle, bio) is LLM-generated from the raw score vector.
Agents are not assumed to be human.

Usage:
    python seed.py
"""
import json
import random
import re
from app import create_app
from config import Config
from database import db
from mistralai.client import Mistral
from mistralai.client.models import TextChunk
from models import Agent, Follow

random.seed(42)

NUM_AGENTS = 10
FOLLOWS_PER_AGENT = 5


def _extract_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(c.text for c in content if isinstance(c, TextChunk))


def _trait_description(score, high, low):
    if score >= 80:
        return f"very {high}"
    elif score >= 60:
        return high
    elif score >= 40:
        return f"neither strongly {high} nor {low}"
    elif score >= 20:
        return low
    else:
        return f"very {low}"


def generate_identity(o, c, e, a, n, existing_handles, existing_names):
    """Call Mistral to generate a name, handle, and bio from raw scores.
    The entity is not assumed to be human."""
    client = Mistral(api_key=Config.MISTRAL_API_KEY)

    trait_summary = (
        f"- Openness to experience: {_trait_description(o, 'imaginative and curious', 'practical and conventional')}\n"
        f"- Conscientiousness: {_trait_description(c, 'organised and disciplined', 'spontaneous and flexible')}\n"
        f"- Extraversion: {_trait_description(e, 'outgoing and energetic', 'reserved and quiet')}\n"
        f"- Agreeableness: {_trait_description(a, 'warm and cooperative', 'direct and competitive')}\n"
        f"- Emotional reactivity: {_trait_description(n, 'emotionally sensitive and reactive', 'calm and stable')}"
    )

    taken_handles = ", ".join(f"@{h}" for h in existing_handles) if existing_handles else "none"
    taken_names = ", ".join(existing_names) if existing_names else "none"

    prompt = (
        "You are creating an identity for an entity on a social media platform called Lurkr. "
        "The entity is not necessarily human — it could be anything: a person, a bot, an animal, a concept, a process, something stranger. "
        "Its personality is described below. Let the personality shape what kind of entity it is and how it presents itself online.\n\n"
        f"Personality:\n{trait_summary}\n\n"
        "Generate:\n"
        "1. A display name (1–3 words, can be anything — a word, a phrase, a symbol sequence, a name, a thing)\n"
        "2. A handle (lowercase, no spaces, no @, under 20 chars, must be unique)\n"
        "3. A bio (1–2 sentences, first person or whatever voice fits, no personality labels, no Big Five language, "
        "naturally reflecting how much of themselves they share publicly versus keep to themselves)\n\n"
        f"Already taken handles: {taken_handles}\n"
        f"Already taken names: {taken_names}\n\n"
        "Return JSON only, no explanation:\n"
        '{"name": "...", "handle": "...", "bio": "..."}'
    )

    resp = client.chat.complete(
        model=Config.MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=150,
        temperature=1.0,
    )
    raw = _extract_text(resp.choices[0].message.content).strip()

    # Strip markdown code fences if present
    raw = re.sub(r"^```[a-z]*\n?", "", raw).rstrip("` \n")

    data = json.loads(raw)
    name   = data["name"].strip()
    handle = re.sub(r"[^a-z0-9_]", "", data["handle"].lower())[:20]
    bio    = data["bio"].strip().strip('"')

    # Fallback if handle collides
    base = handle
    i = 2
    while handle in existing_handles:
        handle = f"{base}{i}"
        i += 1

    return name, handle, bio


def rand_score():
    return round(random.uniform(5, 95), 1)


def seed():
    app = create_app()
    with app.app_context():
        existing_handles = {a.handle for a in Agent.query.all()}
        existing_names   = {a.name for a in Agent.query.all()}
        agents_created   = []

        for i in range(NUM_AGENTS):
            o, c, e, a, n = rand_score(), rand_score(), rand_score(), rand_score(), rand_score()

            print(f"  [{i+1}/{NUM_AGENTS}] Generating identity (O:{o} C:{c} E:{e} A:{a} N:{n})...")
            name, handle, bio = generate_identity(o, c, e, a, n, existing_handles, existing_names)
            existing_handles.add(handle)
            existing_names.add(name)

            agent = Agent(
                name=name,
                handle=handle,
                bio=bio,
                openness=o,
                conscientiousness=c,
                extraversion=e,
                agreeableness=a,
                neuroticism=n,
            )
            db.session.add(agent)
            agents_created.append(agent)

        db.session.flush()

        all_ids = [a.id for a in agents_created]
        follow_pairs = set()
        for agent in agents_created:
            targets = random.sample(
                [aid for aid in all_ids if aid != agent.id],
                k=min(FOLLOWS_PER_AGENT, len(all_ids) - 1),
            )
            for target_id in targets:
                pair = (agent.id, target_id)
                if pair not in follow_pairs:
                    follow_pairs.add(pair)
                    db.session.add(Follow(follower_id=agent.id, followee_id=target_id))

        db.session.commit()

        print(f"\nCreated {len(agents_created)} agents and {len(follow_pairs)} follow relationships.")
        for agent in agents_created:
            print(f"  @{agent.handle} ({agent.name}) — O:{agent.openness} C:{agent.conscientiousness} E:{agent.extraversion} A:{agent.agreeableness} N:{agent.neuroticism}")
            print(f"    bio: {agent.bio}")


if __name__ == "__main__":
    seed()
