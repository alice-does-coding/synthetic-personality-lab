"""
Seed the database with agents with fully randomised Big Five scores.
Bios are generated from the scores — no archetype labels.

Usage:
    python seed.py
"""
import random
from app import create_app
from database import db
from models import Agent, Follow

random.seed(42)

NUM_AGENTS = 10
FOLLOWS_PER_AGENT = 5

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

_BIO_PARTS = {
    "O_high": [
        "probably thinking about something you've never heard of",
        "connects dots that weren't supposed to connect",
        "living in the hypotheticals",
        "gets distracted by ideas mid-sentence",
        "brain permanently in tangent mode",
    ],
    "O_low": [
        "no-nonsense",
        "says what it is",
        "not here for your metaphors",
        "keeps it concrete",
        "straight talker, zero fluff",
    ],
    "C_high": [
        "never misses a deadline",
        "has a system for everything",
        "inbox zero is a lifestyle",
        "reliable to a fault",
        "the one who actually reads the manual",
    ],
    "C_low": [
        "winging it professionally",
        "future plans: tbd",
        "chaos is a lifestyle",
        "definitely forgot something",
        "organized by vibes",
    ],
    "E_high": [
        "will talk to anyone",
        "loudest person in the room",
        "social battery: always charged",
        "loves a crowd",
        "has never eaten lunch alone by choice",
    ],
    "E_low": [
        "better in text",
        "do not disturb",
        "chronically online, rarely social",
        "replies eventually",
        "presence optional",
    ],
    "A_high": [
        "genuinely cares",
        "softie",
        "here if you need to talk",
        "community > clout",
        "remembers your birthday without being reminded",
    ],
    "A_low": [
        "not here to be liked",
        "says what others won't",
        "zero patience for nonsense",
        "you've been warned",
        "diplomatically immune",
    ],
    "N_high": [
        "anxious but posting",
        "catastrophising professionally",
        "it's giving spiral",
        "definitely fine (not fine)",
        "overthinks everything, posts about it anyway",
    ],
    "N_low": [
        "unbothered",
        "nothing phases me",
        "emotionally stable (allegedly)",
        "zen as hell",
        "crisis? what crisis",
    ],
}


def generate_bio(o, c, e, a, n):
    scores = {"O": o, "C": c, "E": e, "A": a, "N": n}
    ranked = sorted(scores.items(), key=lambda x: abs(x[1] - 50), reverse=True)
    parts = []
    for trait, score in ranked[:2]:
        level = "high" if score >= 50 else "low"
        key = f"{trait}_{level}"
        if key in _BIO_PARTS:
            parts.append(random.choice(_BIO_PARTS[key]))
    return ". ".join(parts) + "." if parts else "just here."


def rand_score():
    """Uniformly random OCEAN score, 5–95."""
    return round(random.uniform(5, 95), 1)


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
        agents_created   = []

        for _ in range(NUM_AGENTS):
            o, c, e, a, n = rand_score(), rand_score(), rand_score(), rand_score(), rand_score()

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
                    full = f"{first} {last}{len(agents_created)}"
                    break

            handle = make_handle(first, last, existing_handles)
            existing_handles.add(handle)

            agent = Agent(
                name=full,
                handle=handle,
                bio=generate_bio(o, c, e, a, n),
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

        print(f"Created {len(agents_created)} agents and {len(follow_pairs)} follow relationships.")
        for agent in agents_created:
            print(f"  @{agent.handle} — O:{agent.openness} C:{agent.conscientiousness} E:{agent.extraversion} A:{agent.agreeableness} N:{agent.neuroticism}")
            print(f"    bio: {agent.bio}")


if __name__ == "__main__":
    seed()
