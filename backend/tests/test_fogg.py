"""
Unit tests for fogg.py — B=MAP behavior selection.

No DB, no Flask, no LLM. Pure personality × prompt → action logic.
"""

import pytest
from fogg import select_action, BEHAVIOR_THRESHOLD


# ── Helpers ───────────────────────────────────────────────────────────────────

def snap(O=60, C=55, E=50, A=62, N=45):
    return {
        "openness": O, "conscientiousness": C,
        "extraversion": E, "agreeableness": A, "neuroticism": N,
    }


def post(sentiment=None):
    return {"id": 1, "content": "test post", "sentiment": sentiment}


def headline(category="World"):
    return {"title": "Test headline", "source": "BBC", "category": category, "url": "", "summary": ""}


# ── Reply motivation ───────────────────────────────────────────────────────────

def test_high_extraversion_fires_reply():
    """High-E agent with feed available should reply."""
    s = snap(E=90)
    action = select_action(s, [post()], [])
    assert action is not None
    assert action["type"] == "reply"


def test_low_extraversion_low_conscientiousness_may_go_silent():
    """Low-E, low-C agent with only an organic option may stay quiet."""
    # Run many times — organic motivation for E=10, C=10 is 0.10 + 0.025 + 0.02 = 0.145,
    # well below threshold. With jitter it should almost always be silent.
    s = snap(E=10, C=10)
    results = [select_action(s, [], []) for _ in range(50)]
    silent_count = sum(1 for r in results if r is None)
    assert silent_count >= 40, f"Expected mostly silent, got {silent_count}/50 silent"


def test_high_n_negative_post_boosts_reply():
    """High-N agent replying to a negative post should have higher motivation than neutral."""
    from fogg import _motivation_reply, _ocean
    high_n = snap(N=90, E=50)
    o = _ocean(high_n)
    m_negative = _motivation_reply(o, post_sentiment=-0.8)
    m_neutral  = _motivation_reply(o, post_sentiment=0.0)
    assert m_negative > m_neutral


def test_high_agreeableness_positive_post_boosts_reply():
    """High-A agent should be more motivated to reply to positive content."""
    from fogg import _motivation_reply, _ocean
    high_a = snap(A=90, E=50)
    o = _ocean(high_a)
    m_positive = _motivation_reply(o, post_sentiment=0.8)
    m_negative = _motivation_reply(o, post_sentiment=-0.8)
    assert m_positive > m_negative


# ── News motivation ────────────────────────────────────────────────────────────

def test_high_n_prefers_negative_news_category():
    """High-N agent should have higher motivation for Politics/Health than Science."""
    from fogg import _motivation_news, _ocean
    high_n = snap(N=90)
    o = _ocean(high_n)
    m_politics = _motivation_news(o, "Politics")
    m_science  = _motivation_news(o, "Science")
    assert m_politics > m_science


def test_high_openness_engages_with_science():
    """High-O agent should have higher motivation for Science/Technology."""
    from fogg import _motivation_news, _ocean
    high_o = snap(O=90, N=20)
    o = _ocean(high_o)
    m_science   = _motivation_news(o, "Science")
    m_politics  = _motivation_news(o, "Politics")
    assert m_science > m_politics


def test_high_n_selects_politics_over_science():
    """High-N agent with both Politics and Science headlines should pick Politics."""
    s = snap(N=90, O=40, E=20, C=20)
    politics = headline("Politics")
    science  = headline("Science")
    # Run multiple times and confirm Politics wins more often
    results = [select_action(s, [], [politics, science]) for _ in range(30)]
    news_actions = [r for r in results if r and r["type"] == "news"]
    politics_count = sum(1 for r in news_actions if r["headline"]["category"] == "Politics")
    science_count  = sum(1 for r in news_actions if r["headline"]["category"] == "Science")
    assert politics_count > science_count


# ── Organic motivation ─────────────────────────────────────────────────────────

def test_high_c_high_e_fires_organic():
    """High-C, high-E agent with no feed or headlines should post organically."""
    s = snap(C=90, E=85)
    results = [select_action(s, [], []) for _ in range(20)]
    organic_count = sum(1 for r in results if r and r["type"] == "organic")
    assert organic_count >= 15, f"Expected mostly organic, got {organic_count}/20"


def test_low_c_low_e_rarely_organic():
    """Low-C, low-E agent with no prompts should mostly stay quiet."""
    s = snap(C=10, E=10)
    results = [select_action(s, [], []) for _ in range(30)]
    silent_count = sum(1 for r in results if r is None)
    assert silent_count >= 20, f"Expected mostly silent, got {silent_count}/30 silent"


# ── Action selection ───────────────────────────────────────────────────────────

def test_no_candidates_returns_none():
    """Agent with no feed, no headlines, and low organic motivation returns None."""
    s = snap(C=10, E=10)
    # Run enough times that we can assert None appears
    results = [select_action(s, [], []) for _ in range(20)]
    assert any(r is None for r in results)


def test_reply_beats_organic_for_high_e():
    """High-E agent should prefer replying over posting organically when feed is available."""
    s = snap(E=90, C=50)
    results = [select_action(s, [post(sentiment=0.0)], []) for _ in range(30)]
    fired = [r for r in results if r is not None]
    reply_count   = sum(1 for r in fired if r["type"] == "reply")
    organic_count = sum(1 for r in fired if r["type"] == "organic")
    assert reply_count > organic_count


def test_action_types_are_valid():
    """select_action only ever returns known types or None."""
    s = snap()
    for _ in range(20):
        action = select_action(s, [post()], [headline()])
        assert action is None or action["type"] in ("reply", "news", "organic")


def test_reply_action_contains_post():
    """Reply action includes the post dict."""
    s = snap(E=95)
    p = post(sentiment=0.5)
    results = [select_action(s, [p], []) for _ in range(20)]
    reply_actions = [r for r in results if r and r["type"] == "reply"]
    assert len(reply_actions) > 0
    for r in reply_actions:
        assert "post" in r
        assert r["post"]["id"] == p["id"]


def test_news_action_contains_headline():
    """News action includes the headline dict."""
    s = snap(N=90, E=10, C=10)
    h = headline("Politics")
    results = [select_action(s, [], [h]) for _ in range(20)]
    news_actions = [r for r in results if r and r["type"] == "news"]
    assert len(news_actions) > 0
    for r in news_actions:
        assert "headline" in r
        assert r["headline"]["category"] == "Politics"


# ── Motivation bounds ──────────────────────────────────────────────────────────

def test_motivation_values_in_range():
    """All motivation functions return values in [0, 1]."""
    from fogg import _motivation_reply, _motivation_news, _motivation_organic, _ocean
    for e in [5, 50, 95]:
        for n in [5, 50, 95]:
            o = _ocean(snap(E=e, N=n))
            assert 0.0 <= _motivation_reply(o, 0.0)   <= 1.0
            assert 0.0 <= _motivation_reply(o, -0.8)  <= 1.0
            assert 0.0 <= _motivation_news(o, "Politics") <= 1.0
            assert 0.0 <= _motivation_news(o, "Science")  <= 1.0
            assert 0.0 <= _motivation_organic(o)       <= 1.0
