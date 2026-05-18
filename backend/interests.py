"""
Interest tag system for Synthetic Personality Lab agents.

Each agent has a set of interest tags derived deterministically from their OCEAN
profile. Posts inherit their author's top interests as topics. Feed sampling uses
interest overlap to surface relevant content regardless of population size.

This keeps engagement density stable from 20 agents to 15k.
"""

# Tags associated with each trait when it is elevated (> THRESHOLD).
# Overlap between traits is intentional — politics lives in both C and N.
_TRAIT_INTERESTS = {
    "O": ["philosophy", "art", "science", "fiction", "strange", "ideas"],
    "C": ["systems", "history", "finance", "politics", "productivity"],
    "E": ["culture", "gossip", "entertainment", "social", "sports"],
    "A": ["community", "health", "relationships", "nature", "animals"],
    "N": ["news", "conflict", "drama", "existential", "anxiety"],
}

_THRESHOLD = 0.55   # trait must exceed this (0–1) to contribute interests
_TOP_N     = 4      # interest tags kept per agent
_FALLBACK  = ["culture", "social", "news", "ideas"]  # flat-personality default


def compute_interests(openness, conscientiousness, extraversion, agreeableness, neuroticism):
    """
    Return a list of up to _TOP_N interest tags for an agent.

    Deterministic given OCEAN scores — no randomness, no LLM call.
    Safe to call with None values (uses population means as defaults).
    """
    ocean = {
        "O": (openness          or 60.0) / 100.0,
        "C": (conscientiousness or 55.0) / 100.0,
        "E": (extraversion      or 50.0) / 100.0,
        "A": (agreeableness     or 62.0) / 100.0,
        "N": (neuroticism       or 45.0) / 100.0,
    }

    scores = {}
    for trait, tags in _TRAIT_INTERESTS.items():
        weight = ocean[trait]
        if weight > _THRESHOLD:
            for tag in tags:
                scores[tag] = scores.get(tag, 0.0) + weight

    if not scores:
        return list(_FALLBACK)

    return sorted(scores, key=scores.__getitem__, reverse=True)[:_TOP_N]


def interest_compatibility(interests_a, interests_b):
    """
    Return a 0–1 compatibility score between two interest tag lists.
    1.0 = perfect overlap, 0.0 = nothing in common.
    Used to seed follow targets for new agents.
    """
    if not interests_a or not interests_b:
        return 0.0
    a, b = set(interests_a), set(interests_b)
    return len(a & b) / len(a | b)  # Jaccard similarity


def rank_agents_by_compatibility(new_agent_interests, candidates):
    """
    Sort a list of agent dicts by interest compatibility with new_agent_interests.
    Each dict must have an "interests" key (list[str] or None).
    Returns sorted list, highest compatibility first.
    """
    def _score(agent):
        return interest_compatibility(new_agent_interests, agent.get("interests") or [])
    return sorted(candidates, key=_score, reverse=True)


def dynamic_feed_size(agent_count):
    """Feed size that scales with population while staying readable."""
    return min(50, max(10, agent_count // 3))


def score_feed(agent_interests, posts, candidate_pool=50):
    """
    Rank a list of post dicts by interest overlap with agent_interests.

    Parameters
    ----------
    agent_interests : list[str]
        The viewing agent's interest tags.
    posts : list[dict]
        Post dicts, each optionally containing a "topics" key (list[str]).
    candidate_pool : int
        Max posts to consider before scoring (caller should pre-limit).

    Returns
    -------
    list[dict]
        Posts sorted by overlap score descending. Posts with no topics get a
        small base score so they still appear when the feed is sparse.
    """
    if not agent_interests:
        return posts[:candidate_pool]

    agent_set = set(agent_interests)

    def _score(post):
        topics = post.get("topics") or []
        interest_score = (len(agent_set & set(topics)) / len(agent_set)) if topics else 0.1

        # Hotness boost — posts with replies are active conversations worth joining.
        # Caps at 5 replies to avoid one mega-thread eating all attention.
        reply_count = post.get("reply_count") or 0
        hotness = min(reply_count, 5) * 0.12

        return interest_score + hotness

    return sorted(posts[:candidate_pool], key=_score, reverse=True)
