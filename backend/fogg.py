"""
B = MAP — Fogg Behavior Model for Synthetic Personality Lab agents.

Motivation is a function of OCEAN personality and prompt characteristics.
Ability is uniform — agents can always post (reserved for future extension).
Prompt is the incoming stimulus: a feed post to reply to, a news headline,
or an organic impulse.

B fires when motivation ≥ BEHAVIOR_THRESHOLD.

Usage:
    from fogg import select_action

    action = select_action(snap, feed_posts, headlines)
    # returns {"type": "reply"|"news"|"organic", ...} or None (agent stays quiet)
"""

import random

# Minimum motivation to fire behavior. Below this the agent stays quiet this tick.
BEHAVIOR_THRESHOLD = 0.30

# News categories associated with negative/anxiety-laden valence.
_NEGATIVE_CATEGORIES = {"Politics", "Business", "World", "Health"}
_POSITIVE_CATEGORIES = {"Science", "Technology"}


def _n(score):
    """Normalize a 0–100 OCEAN score to 0–1, defaulting to population mean."""
    _DEFAULTS = {"O": 60, "C": 55, "E": 50, "A": 62, "N": 45}
    return (score or _DEFAULTS.get("O", 50)) / 100.0


def _ocean(snap):
    return {
        "O": (snap.get("openness")          or 60.0) / 100.0,
        "C": (snap.get("conscientiousness") or 55.0) / 100.0,
        "E": (snap.get("extraversion")      or 50.0) / 100.0,
        "A": (snap.get("agreeableness")     or 62.0) / 100.0,
        "N": (snap.get("neuroticism")       or 45.0) / 100.0,
    }


def _motivation_reply(o, post_sentiment):
    """
    How compelled is this agent to reply to a specific post?

    Extraversion drives social engagement. High N + negative content creates
    anxious engagement. Low A + negative content creates combative engagement
    (still engages — disagreement is social too).
    """
    E, N, A = o["E"], o["N"], o["A"]

    m = 0.25 + (E * 0.45)  # extraversion is the primary driver

    if post_sentiment is not None:
        if post_sentiment < -0.3:
            m += N * 0.30           # high-N pulled toward distressing content
            m += (1 - A) * 0.10     # low-A more likely to push back
        elif post_sentiment > 0.3:
            m += A * 0.20           # high-A responds warmly to positive content

    return min(1.0, m)


def _motivation_news(o, category):
    """
    How motivated is this agent to respond to a news headline?

    High N is drawn to anxiety-adjacent categories (politics, health, world).
    High O is curious about everything. High C engages with substantive topics.
    """
    O, C, E, N = o["O"], o["C"], o["E"], o["N"]

    m = 0.15 + (O * 0.20)  # openness = base curiosity

    if category in _NEGATIVE_CATEGORIES:
        m += N * 0.35   # high-N gravitates toward negative/heavy news
        m += C * 0.10   # high-C engages with consequential topics
    elif category in _POSITIVE_CATEGORIES:
        m += O * 0.20   # high-O enjoys novel/curious content
        m += E * 0.10   # high-E engages with energizing topics
    else:
        m += O * 0.10

    return min(1.0, m)


def _motivation_organic(o):
    """
    How motivated is this agent to post an unprompted thought?

    High C posts on a self-directed schedule. High E broadcasts regardless.
    Low C + low E agents rarely initiate — they respond, they don't originate.
    """
    C, E = o["C"], o["E"]
    m = 0.10 + (C * 0.30) + (E * 0.20)
    return min(1.0, m)


def select_action(snap, feed_posts, headlines):
    """
    Apply B=MAP to select what this agent does this tick.

    Parameters
    ----------
    snap : dict
        Agent snapshot (must include OCEAN keys and 'id').
    feed_posts : list[dict]
        Posts available to reply to. Each dict: {id, content, sentiment}.
    headlines : list[dict]
        News headlines available. Each dict: {title, source, category, url, summary}.

    Returns
    -------
    dict or None
        One of:
          {"type": "reply",   "post": {id, content}}
          {"type": "news",    "headline": {title, source, category, url, summary}}
          {"type": "organic"}
        Returns None if no prompt clears the motivation threshold.
    """
    o = _ocean(snap)
    candidates = []

    # Score each potential reply target
    for post in feed_posts:
        sentiment = post.get("sentiment")
        m = _motivation_reply(o, sentiment)
        candidates.append((m, {"type": "reply", "post": post}))

    # Score each available headline
    for headline in headlines:
        m = _motivation_news(o, headline.get("category", ""))
        candidates.append((m, {"type": "news", "headline": headline}))

    # Always include organic as a fallback option
    # Boost organic motivation when feed is empty — even introverts speak into silence
    m_organic = _motivation_organic(o)
    if not feed_posts:
        m_organic = min(1.0, m_organic + 0.10)
    candidates.append((m_organic, {"type": "organic"}))

    # Add jitter so equal motivations don't always resolve the same way
    scored = [(m + random.gauss(0, 0.04), action) for m, action in candidates]
    scored.sort(key=lambda x: x[0], reverse=True)

    best_m, best_action = scored[0]
    if best_m < BEHAVIOR_THRESHOLD:
        return None  # agent stays quiet this tick

    return best_action
