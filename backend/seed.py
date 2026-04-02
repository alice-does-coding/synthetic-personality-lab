"""
Seed the database with agents with fully randomised Big Five scores.
Bios are LLM-generated from the raw score vector — no templates, no archetype labels.

Usage:
    python seed.py
"""
import random
from app import create_app
from config import Config
from database import db
from mistralai.client import Mistral
from mistralai.client.models import TextChunk
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


def _trait_description(score, high, low):
    """Convert a 0–100 score to a plain-English intensity phrase."""
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


def generate_bio(name, handle, o, c, e, a, n):
    """Call Mistral to write a short, neutral first-person bio from raw scores."""
    client = Mistral(api_key=Config.MISTRAL_API_KEY)

    trait_summary = (
        f"- Openness to experience: {_trait_description(o, 'imaginative and curious', 'practical and conventional')}\n"
        f"- Conscientiousness: {_trait_description(c, 'organised and disciplined', 'spontaneous and flexible')}\n"
        f"- Extraversion: {_trait_description(e, 'outgoing and energetic', 'reserved and quiet')}\n"
        f"- Agreeableness: {_trait_description(a, 'warm and cooperative', 'direct and competitive')}\n"
        f"- Emotional reactivity: {_trait_description(n, 'emotionally sensitive and reactive', 'calm and stable')}"
    )

    prompt = (
        f"You are writing a short Twitter/social media bio for a person named {name} (@{handle}).\n\n"
        f"Their personality traits are:\n{trait_summary}\n\n"
        "Write a 1–2 sentence first-person bio that feels authentic to this person. "
        "Do not mention personality traits, psychology, or the Big Five by name. "
        "Do not use the words 'introvert', 'extrovert', 'anxious', 'neurotic', 'agreeable', 'conscientious', or 'openness'. "
        "Write as if this person wrote their own bio — casual, specific, a little idiosyncratic. "
        "No hashtags. No emojis. Return only the bio text, nothing else."
    )

    resp = client.chat.complete(
        model=Config.MISTRAL_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=80,
        temperature=0.95,
    )
    content = resp.choices[0].message.content
    if isinstance(content, list):
        content = "".join(c.text for c in content if isinstance(c, TextChunk))
    return (content or "").strip().strip('"')


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

        for i in range(NUM_AGENTS):
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

            print(f"  [{i+1}/{NUM_AGENTS}] Generating bio for @{handle}...")
            bio = generate_bio(full, handle, o, c, e, a, n)

            agent = Agent(
                name=full,
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
            print(f"  @{agent.handle} — O:{agent.openness} C:{agent.conscientiousness} E:{agent.extraversion} A:{agent.agreeableness} N:{agent.neuroticism}")
            print(f"    bio: {agent.bio}")


if __name__ == "__main__":
    seed()
