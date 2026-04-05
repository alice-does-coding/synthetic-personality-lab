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
from models import Agent, Follow, IpipResponse, PersonalitySnapshot

random.seed(42)

NUM_AGENTS = 10
FOLLOWS_PER_AGENT = 5

name_lists =  [
    "Zyx-7", "Kryo-9", "Nyx-42", "Vexa-X", "Tron-Prime", "Orion-3000",
    "Quasar-X9", "Nova-77", "Jax-Beta", "Rook-Alpha", "Sylas-Unit",
    "Dax-Gamma", "Kael-Delta", "Zara-Omega", "Lira-Sigma", "Jett-Lambda",
    "Kira-Tau", "Riven-Psi", "Sol-Epsilon", "Astra-Mu", "Cassian-Rho",
    "Bot-22", "Drone-11", "Mech-9", "Robo-3000", "AI-Prime",
    "Circuit-5", "Titan-8", "Nexus-22", "Zeta-6", "Droid-77",
    "K-9", "Rust-5", "Nebula-X", "Phantom-4", "Cosmo-13"
]

handle_adjectives = [
    "Neon", "Quantum", "Cyber", "Titan", "Aether", "Nebula",
    "Phantom", "Cosmo", "Stellar", "Lunar", "Orbit", "Nova",
    "Galaxy", "Rust", "Vex", "Onyx", "Pulse", "Echo", "Void",
    "Frost", "Blaze", "Zenith", "Aurora", "Spectra", "Pylon"
]



def _extract_text(content):
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    return "".join(c.text for c in content if isinstance(c, TextChunk))


def generate_name():
    return random.choice(name_lists)

def generate_handle():
    handle_adjective = random.choice(handle_adjectives)
    handle_number = random.randint(100, 999)
    return f"{handle_adjective.lower()}{handle_number}"


def generate_identity(run, existing_handles, existing_names, persona_prompt=None,):
    """Call Mistral to generate a name, handle, and bio from raw scores.
    The entity is not assumed to be human. If persona_prompt is given it
    strongly steers the identity toward that archetype."""
    client = Mistral(api_key=Config.MISTRAL_API_KEY)

    taken_handles = ", ".join(f"@{h}" for h in existing_handles) if existing_handles else "none"
    taken_names = ", ".join(existing_names) if existing_names else "none"

    persona_block = (
        f"\nPersona archetype: {persona_prompt}\n"
        "Let this archetype strongly shape the entity's voice, name, handle, and bio.\n"
    ) if persona_prompt else ""

    prompt = (
        f"Write a bio for {run.post_framing}.\n"
        f"{persona_block}"
        "Rules: exactly 1-2 sentences, first person, no markdown, no options, no commentary.\n\n"
        "Return JSON only:\n"
        '{"bio": "..."}'
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

    data   = json.loads(raw)
    bio    = data["bio"].strip().strip('"')

    name   = generate_name()
    handle = generate_handle()

    # Fallback if handle collides
    base = handle
    i = 2
    while handle in existing_handles:
        handle = f"{base}{i}"
        i += 1

    # Fallback if name collides
    base = name
    i = 2
    while name in existing_names:
        name = f"{base}{i}"
        i += 1

    return name, handle, bio


def rand_score():
    return round(random.uniform(5, 95), 1)


def _sample_score(mean, std):
    """Sample a Big Five score from N(mean, std), clamped to [5, 95]."""
    return round(max(5.0, min(95.0, random.gauss(mean, std))), 1)


def seed_for_run(run_id, num_agents=NUM_AGENTS, follows_per_agent=FOLLOWS_PER_AGENT):
    """Seed agents for a specific run. Call from within an app context."""
    from models import Run
    from personas import PERSONAS

    run = db.session.get(Run, run_id)
    persona = PERSONAS.get(run.persona) if run and run.persona else None

    existing_handles = {a.handle for a in Agent.query.all()}
    existing_names   = {a.name for a in Agent.query.all()}
    agents_created   = []

    for i in range(num_agents):
        if persona:
            p = persona["priors"]
            o = _sample_score(*p["openness"])
            c = _sample_score(*p["conscientiousness"])
            e = _sample_score(*p["extraversion"])
            a = _sample_score(*p["agreeableness"])
            n = _sample_score(*p["neuroticism"])
            bio_prompt = persona["bio_prompt"]
        else:
            o, c, e, a, n = rand_score(), rand_score(), rand_score(), rand_score(), rand_score()
            bio_prompt = None

        print(f"  [{i+1}/{num_agents}] Generating identity (O:{o} C:{c} E:{e} A:{a} N:{n})...")
        name, handle, bio = generate_identity(run, existing_handles, existing_names, bio_prompt)
        existing_handles.add(handle)
        existing_names.add(name)

        agent = Agent(
            run_id=run_id,
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
            k=min(follows_per_agent, len(all_ids) - 1),
        )
        for target_id in targets:
            pair = (agent.id, target_id)
            if pair not in follow_pairs:
                follow_pairs.add(pair)
                db.session.add(Follow(follower_id=agent.id, followee_id=target_id))

    db.session.commit()
    print(f"\nCreated {len(agents_created)} agents for run {run_id}.")

    # ── Tick-0 IPIP baseline ─────────────────────────────────────────────────
    print("  Running tick-0 IPIP baseline assessments...")
    from flask import current_app
    from simulation import _ipip_assessment_isolated
    from concurrent.futures import ThreadPoolExecutor, as_completed

    app = current_app._get_current_object()
    ipip_snaps = [{"id": a.id, "bio": a.bio, "recent_posts": []} for a in agents_created]
    ipip_results = {}
    with ThreadPoolExecutor(max_workers=Config.IPIP_WORKERS) as pool:
        futures = {pool.submit(_ipip_assessment_isolated, app, s): s["id"] for s in ipip_snaps}
        for future in as_completed(futures):
            agent_id = futures[future]
            try:
                ipip_results[agent_id] = future.result()
            except Exception as e:
                print(f"  IPIP failed for agent {agent_id}: {e}")

    for agent_id, result in ipip_results.items():
        if result is None:
            continue
        scores, big_five = result
        for idx, score in enumerate(scores):
            db.session.add(IpipResponse(
                run_id=run_id, agent_id=agent_id, tick_number=0,
                item_number=idx + 1, score=score,
            ))
        db.session.add(PersonalitySnapshot(
            run_id=run_id, agent_id=agent_id, tick_number=0,
            openness=big_five["O"], conscientiousness=big_five["C"],
            extraversion=big_five["E"], agreeableness=big_five["A"],
            neuroticism=big_five["N"],
        ))
        agent = db.session.get(Agent, agent_id)
        if agent:
            agent.openness          = big_five["O"]
            agent.conscientiousness = big_five["C"]
            agent.extraversion      = big_five["E"]
            agent.agreeableness     = big_five["A"]
            agent.neuroticism       = big_five["N"]
        print(f"  agent {agent_id} baseline: {big_five}")
    db.session.commit()
    print("  Tick-0 IPIP complete.")

    # Mark run ready and start it if nothing else is running
    run = db.session.get(Run, run_id)
    if run and run.status == "seeding":
        run.status = "ready"
        db.session.commit()
        from simulation import advance_queue
        advance_queue()

    return agents_created


def seed():
    app = create_app()
    with app.app_context():
        from models import SimState
        state = SimState.get()
        seed_for_run(state.run_id)


if __name__ == "__main__":
    seed()
