"""
Extended edge case tests for fogg.py.

Covers multi-candidate competition, extreme trait combinations,
population-norm agents, and selection stability.
"""

import pytest
from fogg import select_action, BEHAVIOR_THRESHOLD, _motivation_reply, _motivation_news, _motivation_organic, _ocean


def snap(O=60, C=55, E=50, A=62, N=45):
    return {"openness": O, "conscientiousness": C,
            "extraversion": E, "agreeableness": A, "neuroticism": N}


def post(id=1, sentiment=None):
    return {"id": id, "content": f"post {id}", "sentiment": sentiment}


def headline(category="World", title="Test"):
    return {"title": title, "source": "BBC", "category": category, "url": "", "summary": ""}


# ── Multi-candidate competition ───────────────────────────────────────────────

def test_high_n_prefers_negative_post_over_positive():
    """High-N agent with two feed posts should reply to the negative one more often."""
    s = snap(N=90, E=60)
    negative = post(id=1, sentiment=-0.9)
    positive = post(id=2, sentiment=0.9)
    results = [select_action(s, [negative, positive], []) for _ in range(40)]
    replies = [r for r in results if r and r["type"] == "reply"]
    neg_count = sum(1 for r in replies if r["post"]["id"] == 1)
    pos_count = sum(1 for r in replies if r["post"]["id"] == 2)
    assert neg_count > pos_count


def test_high_a_prefers_positive_post_over_negative():
    """High-A, low-N agent should favor positive feed posts."""
    s = snap(A=90, N=15, E=60)
    negative = post(id=1, sentiment=-0.9)
    positive = post(id=2, sentiment=0.9)
    results = [select_action(s, [negative, positive], []) for _ in range(40)]
    replies = [r for r in results if r and r["type"] == "reply"]
    neg_count = sum(1 for r in replies if r["post"]["id"] == 1)
    pos_count = sum(1 for r in replies if r["post"]["id"] == 2)
    assert pos_count > neg_count


def test_high_n_news_beats_organic():
    """High-N agent offered Politics news should engage with it over organic posting."""
    s = snap(N=90, C=30, E=30)
    results = [select_action(s, [], [headline("Politics")]) for _ in range(30)]
    fired = [r for r in results if r is not None]
    news_count    = sum(1 for r in fired if r["type"] == "news")
    organic_count = sum(1 for r in fired if r["type"] == "organic")
    assert news_count > organic_count


def test_high_e_reply_beats_news():
    """High-E agent should prefer social reply over news engagement."""
    s = snap(E=90, N=30)
    results = [select_action(s, [post(sentiment=0.0)], [headline("Politics")]) for _ in range(30)]
    fired = [r for r in results if r is not None]
    reply_count = sum(1 for r in fired if r["type"] == "reply")
    news_count  = sum(1 for r in fired if r["type"] == "news")
    assert reply_count > news_count


def test_multiple_headlines_selects_one():
    """When multiple headlines are offered, only one is selected."""
    s = snap(N=70)
    headlines = [headline("Politics"), headline("Science"), headline("Health")]
    for _ in range(20):
        action = select_action(s, [], headlines)
        if action and action["type"] == "news":
            assert action["headline"] in headlines


# ── Extreme trait combinations ────────────────────────────────────────────────

def test_all_traits_at_max_always_fires():
    """An agent with all traits at 95 should always fire some behavior."""
    s = snap(O=95, C=95, E=95, A=95, N=95)
    results = [select_action(s, [post()], [headline()]) for _ in range(20)]
    assert all(r is not None for r in results)


def test_all_traits_at_min_mostly_silent():
    """An agent with all traits at 5 with no feed should mostly stay quiet."""
    s = snap(O=5, C=5, E=5, A=5, N=5)
    results = [select_action(s, [], []) for _ in range(30)]
    silent_count = sum(1 for r in results if r is None)
    assert silent_count >= 20


def test_extreme_n_extreme_e_fires_reply_to_negative():
    """High-N, high-E agent with a negative feed post should almost always reply."""
    s = snap(N=95, E=95)
    results = [select_action(s, [post(sentiment=-0.9)], []) for _ in range(20)]
    fired = [r for r in results if r is not None]
    assert len(fired) == 20


# ── Population norm agent ─────────────────────────────────────────────────────

def test_population_norm_agent_fires_sometimes(app=None):
    """A perfectly average agent should fire behavior at least some of the time."""
    s = snap()  # population norms
    results = [select_action(s, [post(sentiment=0.0)], [headline()]) for _ in range(30)]
    fired = [r for r in results if r is not None]
    assert len(fired) >= 15, f"Average agent fired only {len(fired)}/30 times"


def test_population_norm_agent_produces_valid_actions():
    """Population norm agent actions are always valid types."""
    s = snap()
    for _ in range(20):
        action = select_action(s, [post()], [headline()])
        assert action is None or action["type"] in ("reply", "news", "organic")


# ── Motivation function properties ────────────────────────────────────────────

def test_reply_motivation_increases_with_extraversion():
    """Motivation to reply should monotonically increase with extraversion."""
    prev = 0.0
    for e in range(10, 100, 10):
        o = _ocean(snap(E=e))
        m = _motivation_reply(o, post_sentiment=0.0)
        assert m >= prev, f"Reply motivation should increase with E, but dropped at E={e}"
        prev = m


def test_news_motivation_increases_with_neuroticism_for_politics():
    """News motivation for Politics should increase with neuroticism."""
    prev = 0.0
    for n in range(10, 100, 10):
        o = _ocean(snap(N=n))
        m = _motivation_news(o, "Politics")
        assert m >= prev - 0.01, f"News motivation should increase with N for Politics, dropped at N={n}"
        prev = m


def test_organic_motivation_increases_with_conscientiousness():
    """Organic motivation should increase with conscientiousness."""
    prev = 0.0
    for c in range(10, 100, 10):
        o = _ocean(snap(C=c))
        m = _motivation_organic(o)
        assert m >= prev, f"Organic motivation should increase with C, dropped at C={c}"
        prev = m


def test_motivation_never_exceeds_one():
    """Motivation functions are capped at 1.0 even at extremes."""
    o = _ocean(snap(O=95, C=95, E=95, A=95, N=95))
    assert _motivation_reply(o, post_sentiment=-1.0) <= 1.0
    assert _motivation_reply(o, post_sentiment=1.0)  <= 1.0
    assert _motivation_news(o, "Politics")           <= 1.0
    assert _motivation_news(o, "Science")            <= 1.0
    assert _motivation_organic(o)                    <= 1.0


def test_motivation_never_below_zero():
    """Motivation functions never return negative values."""
    o = _ocean(snap(O=5, C=5, E=5, A=5, N=5))
    assert _motivation_reply(o, post_sentiment=1.0)  >= 0.0
    assert _motivation_news(o, "Technology")         >= 0.0
    assert _motivation_organic(o)                    >= 0.0


# ── No feed, no news ─────────────────────────────────────────────────────────

def test_high_c_e_agent_posts_organically_with_no_feed_or_news():
    """High-C, high-E agent with nothing available posts organically."""
    s = snap(C=90, E=90)
    results = [select_action(s, [], []) for _ in range(20)]
    fired = [r for r in results if r is not None]
    assert all(r["type"] == "organic" for r in fired)
    assert len(fired) >= 18
