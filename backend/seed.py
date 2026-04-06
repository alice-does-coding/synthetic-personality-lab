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
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from app import create_app
from config import Config
from database import db
import llm as _llm
from llm import chat as llm_chat, extract_text as llm_extract_text
from models import Agent, Follow, PersonalitySnapshot

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



def generate_name():
    return random.choice(name_lists)

def generate_handle():
    handle_adjective = random.choice(handle_adjectives)
    handle_number = random.randint(100, 999)
    return f"{handle_adjective.lower()}{handle_number}"


def _generate_bio(post_framing, persona_prompt=None, provider="mistral", model=None):
    """Generate a bio via the configured LLM provider. Thread-safe — no shared state."""
    model = model or Config.MISTRAL_POST_MODEL

    persona_block = (
        f"\nPersona archetype: {persona_prompt}\n"
        "Let this archetype strongly shape the entity's voice and bio.\n"
    ) if persona_prompt else ""

    prompt = (
        f"Write a bio for {post_framing}.\n"
        f"{persona_block}"
        "Rules: exactly 1-2 sentences, first person, no markdown, no options, no commentary.\n\n"
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


# IPIP-NEO population norms (mean, sd) — scored 0–100
_POPULATION_NORMS = {
    "openness":          (60, 20),
    "conscientiousness": (55, 20),
    "extraversion":      (50, 22),
    "agreeableness":     (62, 18),
    "neuroticism":       (45, 22),
}

def _sample_population():
    """Sample a realistic Big Five profile from population norms."""
    return {k: _sample_score(*v) for k, v in _POPULATION_NORMS.items()}


def _sample_score(mean, std):
    """Sample a Big Five score from N(mean, std), clamped to [5, 95]."""
    return round(max(5.0, min(95.0, random.gauss(mean, std))), 1)


def seed_for_run(run_id, num_agents=NUM_AGENTS, follows_per_agent=FOLLOWS_PER_AGENT):
    """Seed agents for a specific run. Call from within an app context."""
    from models import Run
    from personas import PERSONAS, GEN1_POKEMON

    run = db.session.get(Run, run_id)
    persona = PERSONAS.get(run.persona) if run and run.persona else None

    # Provider/model for LLM calls during seeding
    run_provider = run.provider if run and run.provider else "mistral"
    run_model    = run.model    if run and run.model    else Config.MISTRAL_POST_MODEL

    # Reproducible seeding when random_seed is set
    if run.random_seed is not None:
        random.seed(run.random_seed)

    is_pokemon  = (run.persona == "pokemon")
    custom_pool = run.name_pool if run.name_pool else None

    if is_pokemon:
        num_agents = len(GEN1_POKEMON)
        name_list  = list(GEN1_POKEMON)
    elif custom_pool:
        num_agents = len(custom_pool)
        name_list  = list(custom_pool)
    else:
        name_list  = None

    existing_handles = {a.handle for a in Agent.query.all()}
    existing_names   = {a.name for a in Agent.query.all()}

    # ── Build score configs upfront ──────────────────────────────────────────
    configs = []
    for i in range(num_agents):
        if persona:
            p = persona["priors"]
            cfg = {
                "o": _sample_score(*p["openness"]),
                "c": _sample_score(*p["conscientiousness"]),
                "e": _sample_score(*p["extraversion"]),
                "a": _sample_score(*p["agreeableness"]),
                "n": _sample_score(*p["neuroticism"]),
                "bio_prompt": persona["bio_prompt"],
            }
        else:
            scores = _sample_population()
            cfg = {
                "o": scores["openness"], "c": scores["conscientiousness"],
                "e": scores["extraversion"], "a": scores["agreeableness"],
                "n": scores["neuroticism"],
                "bio_prompt": None,
            }
        if name_list and i < len(name_list):
            entry = name_list[i]
            cfg["name_override"] = entry
            cfg["handle_base"]   = re.sub(r"[^a-z0-9_]", "", entry.lower().replace(" ", "_").replace("-", "_"))[:30] or f"agent{i}"
            if is_pokemon:
                cfg["bio_framing"] = f"{entry}, an original Generation 1 Pokémon"
            elif custom_pool:
                # Named character pool — stay in character, ignore generic post_framing
                cfg["bio_framing"] = (
                    f"{entry} — write in first person as this real historical figure or fictional character, "
                    "capturing their actual personality, era, role, and voice. Do not invent a modern persona."
                )
        configs.append(cfg)

    # ── Log seeding started ───────────────────────────────────────────────────
    from flask import current_app as _cur_app
    from simulation import log_event
    _app = _cur_app._get_current_object()
    log_event(_app, run_id, "info", f"Seeding started — generating {num_agents} agents")

    # ── Generate all bios in parallel ─────────────────���────────────────────��─
    print(f"  Generating {num_agents} agent bios in parallel...")
    bios = [None] * num_agents
    with ThreadPoolExecutor(max_workers=Config.MAX_WORKERS) as pool:
        futures = {
            pool.submit(
                _generate_bio,
                cfg.get("bio_framing") or run.post_framing,
                cfg["bio_prompt"],
                run_provider,
                run_model,
            ): i
            for i, cfg in enumerate(configs)
        }
        for future in as_completed(futures):
            i = futures[future]
            try:
                bios[i] = future.result()
                print(f"  [{i+1}/{num_agents}] bio done")
            except Exception as exc:
                print(f"  [{i+1}/{num_agents}] bio failed: {exc}")
                bios[i] = "No description available."

    # ── Create agents (name/handle collision-safe, sequential) ───────────────
    agents_created = []
    for i, cfg in enumerate(configs):
        if "name_override" in cfg:
            name = cfg["name_override"]
            base_handle = cfg["handle_base"]
            handle = base_handle
            j = 2
            while handle in existing_handles:
                handle = f"{base_handle}{j}"; j += 1
        else:
            name   = generate_name()
            handle = generate_handle()

        if "name_override" not in cfg:
            base = handle
            j = 2
            while handle in existing_handles:
                handle = f"{base}{j}"; j += 1

            base = name
            j = 2
            while name in existing_names:
                name = f"{base}{j}"; j += 1

        existing_handles.add(handle)
        existing_names.add(name)

        agent = Agent(
            run_id=run_id,
            name=name, handle=handle, bio=bios[i],
            openness=cfg["o"], conscientiousness=cfg["c"],
            extraversion=cfg["e"], agreeableness=cfg["a"],
            neuroticism=cfg["n"],
        )
        db.session.add(agent)
        agents_created.append(agent)

    try:
        db.session.flush()  # assigns IDs; avatars generated next
    except Exception as exc:
        from sqlalchemy.exc import IntegrityError
        if isinstance(exc, IntegrityError) and "agents_handle_key" in str(exc):
            db.session.rollback()
            raise RuntimeError(
                "Handle collision during seeding — retry with a different seed or re-run"
            ) from exc
        raise

    # ── Generate avatars in parallel (best-effort — failures leave avatar=None) ─
    if run_provider == "hf" and Config.HF_API_KEY:
        print(f"  Generating {len(agents_created)} agent avatars in parallel...")
        log_event(_app, run_id, "info", f"Generating {len(agents_created)} agent avatars via FLUX")
        avatars = [None] * len(agents_created)
        with ThreadPoolExecutor(max_workers=min(Config.MAX_WORKERS, 6)) as pool:
            futures = {
                pool.submit(_llm.generate_avatar, run_provider, a.bio, a.name): i
                for i, a in enumerate(agents_created)
            }
            for future in as_completed(futures):
                i = futures[future]
                try:
                    avatars[i] = future.result()
                    if avatars[i]:
                        print(f"  [{i+1}/{len(agents_created)}] avatar ok")
                except Exception as exc:
                    print(f"  [{i+1}/{len(agents_created)}] avatar failed: {exc}")
        for i, agent in enumerate(agents_created):
            if avatars[i]:
                agent.avatar = avatars[i]
        n_ok = sum(1 for a in avatars if a)
        log_event(_app, run_id, "info", f"Avatars generated — {n_ok}/{len(agents_created)} succeeded")

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

    # ── Tick-0 personality snapshots (no LLM — use initial scores directly) ──
    for agent in agents_created:
        db.session.add(PersonalitySnapshot(
            run_id=run_id, agent_id=agent.id, tick_number=0,
            openness=agent.openness, conscientiousness=agent.conscientiousness,
            extraversion=agent.extraversion, agreeableness=agent.agreeableness,
            neuroticism=agent.neuroticism,
        ))

    db.session.commit()
    follow_count = len(follow_pairs)
    print(f"\nCreated {len(agents_created)} agents for run {run_id}.")
    log_event(_app, run_id, "info",
              f"Seeding complete — {len(agents_created)} agents, {follow_count} follows")

    # Mark run as running and spawn its tick thread
    run = db.session.get(Run, run_id)
    if run and run.status == "seeding":
        from datetime import datetime
        run.status = "running"
        run.started_at = datetime.utcnow()
        db.session.commit()
        log_event(_app, run_id, "info", "Run started")
        from simulation import start_run_thread
        start_run_thread(_app, run_id)

    return agents_created


def seed(run_id):
    app = create_app()
    with app.app_context():
        seed_for_run(run_id)


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python seed.py <run_id>")
        sys.exit(1)
    seed(int(sys.argv[1]))
