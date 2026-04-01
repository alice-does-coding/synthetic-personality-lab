"""
Seed the database with 100 agents spanning a range of Big Five personality profiles.
Each agent gets an initial personality score (so posts are flavoured from tick 1)
and follows ~15 randomly chosen others to bootstrap the social graph.

Usage:
    python seed.py
"""
import random
from app import create_app
from database import db
from models import Agent, Follow

random.seed(42)

# ── Personality archetypes ─────────────────────────────────────────────────────
# Each archetype is a base Big Five profile (O, C, E, A, N) on 0-100.
# Agents are sampled from these with Gaussian noise (σ=10, clamped 5-95).

ARCHETYPES = [
    # label,              O     C     E     A     N
    ("The Intellectual",  85,   72,   35,   55,   40),
    ("The Socialite",     60,   50,   90,   75,   30),
    ("The Rebel",         80,   25,   65,   25,   55),
    ("The Caregiver",     55,   70,   60,   90,   35),
    ("The Worrier",       50,   55,   30,   60,   85),
    ("The Dreamer",       90,   30,   45,   65,   50),
    ("The Pragmatist",    35,   88,   50,   55,   25),
    ("The Cynic",         60,   45,   30,   20,   70),
    ("The Performer",     70,   55,   88,   60,   45),
    ("The Stoic",         45,   80,   25,   50,   15),
    ("The Agitator",      65,   30,   70,   15,   65),
    ("The Empath",        75,   60,   55,   92,   55),
    ("The Minimalist",    40,   75,   20,   50,   20),
    ("The Contrarian",    70,   35,   50,   18,   60),
    ("The Enthusiast",    80,   60,   85,   70,   30),
    ("The Recluse",       75,   50,   10,   40,   55),
    ("The Moralist",      45,   90,   45,   80,   30),
    ("The Hedonist",      70,   15,   80,   45,   50),
    ("The Strategist",    65,   85,   55,   40,   30),
    ("The Melancholic",   80,   40,   25,   55,   80),
]

# ── Name pool ──────────────────────────────────────────────────────────────────
FIRST_NAMES = [
    "Alex","Morgan","Jordan","Casey","Riley","Quinn","Avery","Peyton","Reese","Sage",
    "Drew","Blake","Cameron","Charlie","Dakota","Emery","Finley","Hayden","Jamie","Kendall",
    "Lane","Logan","Marlowe","Nico","Oakley","Parker","Remy","Rowan","Sawyer","Shea",
    "Skyler","Sterling","Taylor","Toby","Val","Winter","Wren","Zara","Eli","Nova",
    "Juno","Rafi","Sable","Cleo","Dex","Piper","Luca","Noel","Tate","Indigo",
]
LAST_NAMES = [
    "Voss","Hale","Marsh","Cole","Stone","Park","West","Nash","Gray","Lane",
    "Cruz","Bell","Fox","Reed","Shaw","Knight","Bloom","Cross","Hart","Banks",
    "Wolfe","Price","Dean","Burke","Moon","Flynn","Stark","Wade","York","Crane",
    "Holloway","Mercer","Aldridge","Beckett","Calloway","Durant","Everett","Fairfax",
    "Grayson","Harlow","Ingram","Jennings","Kimura","Laurent","Montes","Navarro",
    "Okafor","Petrov","Quintero","Rashid",
]

# Bio fragments keyed by trait + level. Two are picked and joined.
_BIO_PARTS = {
    "O_high": ["probably thinking about something you've never heard of",
               "connects dots that weren't supposed to connect",
               "living in the hypotheticals",
               "gets distracted by ideas mid-sentence"],
    "O_low":  ["no-nonsense",
               "says what it is",
               "not here for your metaphors",
               "keeps it concrete"],
    "C_high": ["never misses a deadline",
               "has a system for everything",
               "inbox zero is a lifestyle",
               "reliable to a fault"],
    "C_low":  ["winging it professionally",
               "future plans: tbd",
               "chaos is a lifestyle",
               "definitely forgot something"],
    "E_high": ["will talk to anyone",
               "loudest person in the room",
               "social battery: always charged",
               "loves a crowd"],
    "E_low":  ["better in text",
               "do not disturb",
               "chronically online, rarely social",
               "replies eventually"],
    "A_high": ["genuinely cares",
               "softie",
               "here if you need to talk",
               "community > clout"],
    "A_low":  ["not here to be liked",
               "says what others won't",
               "zero patience for nonsense",
               "you've been warned"],
    "N_high": ["anxious but posting",
               "catastrophising professionally",
               "it's giving spiral",
               "definitely fine (not fine)"],
    "N_low":  ["unbothered",
               "nothing phases me",
               "emotionally stable (allegedly)",
               "zen as hell"],
}


def generate_bio(o, c, e, a, n):
    """Pick two bio fragments based on the two most extreme OCEAN scores."""
    scores = {"O": o, "C": c, "E": e, "A": a, "N": n}
    # rank by distance from 50 (most extreme first)
    ranked = sorted(scores.items(), key=lambda x: abs(x[1] - 50), reverse=True)

    parts = []
    for trait, score in ranked[:2]:
        level = "high" if score >= 50 else "low"
        key = f"{trait}_{level}"
        if key in _BIO_PARTS:
            parts.append(random.choice(_BIO_PARTS[key]))

    return ". ".join(parts) + "." if parts else "just here."


def jitter(val, sigma=12):
    return round(max(5.0, min(95.0, random.gauss(val, sigma))), 1)


def make_handle(first, last, existing):
    base = f"{first.lower()}{last.lower()}"
    handle = base
    n = 2
    while handle in existing:
        handle = f"{base}{n}"
        n += 1
    return handle


def seed():
    app = create_app()
    with app.app_context():
        existing_handles = {a.handle for a in Agent.query.all()}
        existing_names   = set()

        agents_to_create = []

        for i in range(100):
            archetype_label, o, c, e, a, n = ARCHETYPES[i % len(ARCHETYPES)]

            # Pick a unique name
            attempts = 0
            while True:
                first = random.choice(FIRST_NAMES)
                last  = random.choice(LAST_NAMES)
                full  = f"{first} {last}"
                if full not in existing_names:
                    existing_names.add(full)
                    break
                attempts += 1
                if attempts > 200:
                    full = f"{first} {last}{i}"
                    break

            handle = make_handle(first, last, existing_handles)
            existing_handles.add(handle)

            bio = generate_bio(
                jitter(o), jitter(c), jitter(e), jitter(a), jitter(n)
            )

            agent = Agent(
                name=full,
                handle=handle,
                bio=bio,
                openness=jitter(o),
                conscientiousness=jitter(c),
                extraversion=jitter(e),
                agreeableness=jitter(a),
                neuroticism=jitter(n),
            )
            db.session.add(agent)
            agents_to_create.append((agent, archetype_label))

        db.session.flush()  # assigns IDs

        # ── Follow graph: each agent follows ~15 random others ────────────────
        all_ids = [a.id for a, _ in agents_to_create]
        follow_pairs = set()

        # Also grab existing agents already in the DB
        existing_agents = Agent.query.filter(
            ~Agent.id.in_(all_ids)
        ).all()
        all_ids_full = all_ids + [a.id for a in existing_agents]

        for agent, _ in agents_to_create:
            targets = random.sample(
                [aid for aid in all_ids_full if aid != agent.id],
                k=min(15, len(all_ids_full) - 1),
            )
            for target_id in targets:
                pair = (agent.id, target_id)
                if pair not in follow_pairs:
                    follow_pairs.add(pair)
                    db.session.add(Follow(follower_id=agent.id, followee_id=target_id))

        db.session.commit()

        print(f"Created {len(agents_to_create)} agents and {len(follow_pairs)} follow relationships.")
        for agent, archetype in agents_to_create[:5]:
            print(f"  @{agent.handle} ({archetype}) — O:{agent.openness} C:{agent.conscientiousness} E:{agent.extraversion} A:{agent.agreeableness} N:{agent.neuroticism}")
        print("  ...")


if __name__ == "__main__":
    seed()
