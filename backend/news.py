"""
News fetcher — pulls headlines from BBC and NPR RSS feeds and caches them.

Headlines are refreshed at most once every REFRESH_MINUTES minutes so we
don't hammer the feeds on every tick.  The module exposes a single function:

    get_headlines(n=5) -> list[dict]

Each headline dict has:
    title    : str   — the headline text
    summary  : str   — one-sentence description (may be empty)
    category : str   — e.g. "Technology", "Politics", "Science" …
    source   : str   — e.g. "BBC", "NPR"
"""

import logging
import random
import re
import time
from threading import Lock

import feedparser
import requests

logger = logging.getLogger(__name__)

REFRESH_MINUTES = 15

FEEDS = [
    # (label, category, url)
    ("BBC",  "World",      "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("BBC",  "Technology", "https://feeds.bbci.co.uk/news/technology/rss.xml"),
    ("BBC",  "Science",    "https://feeds.bbci.co.uk/news/science_and_environment/rss.xml"),
    ("BBC",  "Health",     "https://feeds.bbci.co.uk/news/health/rss.xml"),
    ("BBC",  "Business",   "https://feeds.bbci.co.uk/news/business/rss.xml"),
    ("BBC",  "Politics",   "https://feeds.bbci.co.uk/news/politics/rss.xml"),
    ("NPR",  "World",      "https://feeds.npr.org/1004/rss.xml"),
    ("NPR",  "Politics",   "https://feeds.npr.org/1014/rss.xml"),
    ("NPR",  "Science",    "https://feeds.npr.org/1007/rss.xml"),
    ("NPR",  "Health",     "https://feeds.npr.org/1128/rss.xml"),
]

_HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; lurkr-research/1.0)"}

_cache: list[dict] = []
_last_fetch: float = 0.0
_lock = Lock()


def _fetch_feed(source, category, feed_url, retries=3) -> list[dict]:
    """Fetch a single RSS feed with retry on transient errors."""
    for attempt in range(retries):
        try:
            r = requests.get(feed_url, headers=_HEADERS, timeout=8)
            r.raise_for_status()
            feed = feedparser.parse(r.content)
            items = []
            for entry in feed.entries:
                title = entry.get("title", "").strip()
                summary = entry.get("summary", "").strip()
                summary = re.sub(r"<[^>]+>", "", summary).strip()
                link = entry.get("link", "").strip()
                if title:
                    items.append({
                        "title":    title,
                        "summary":  summary,
                        "category": category,
                        "source":   source,
                        "url":      link,
                    })
            return items
        except Exception as exc:
            if attempt < retries - 1:
                backoff = 2 ** attempt
                logger.warning("Feed fetch error %s %s (attempt %d/%d) — retrying in %ds: %s",
                               source, category, attempt + 1, retries, backoff, exc)
                time.sleep(backoff)
            else:
                logger.warning("Failed to fetch %s %s feed after %d attempts: %s",
                               source, category, retries, exc)
    return []


def _fetch_all() -> list[dict]:
    headlines = []
    for source, category, url in FEEDS:
        headlines.extend(_fetch_feed(source, category, url))
    random.shuffle(headlines)
    return headlines


def _refresh_if_stale():
    global _cache, _last_fetch
    with _lock:
        age_minutes = (time.time() - _last_fetch) / 60
        if age_minutes < REFRESH_MINUTES and _cache:
            return
        logger.info("Refreshing news headlines…")
        fresh = _fetch_all()
        if fresh:
            _cache = fresh
            _last_fetch = time.time()
            logger.info("Fetched %d headlines across %d feeds", len(fresh), len(FEEDS))
        else:
            logger.warning("No headlines fetched — keeping stale cache")


def get_headlines(n: int = 5) -> list[dict]:
    """Return n random headlines, refreshing the cache if stale."""
    _refresh_if_stale()
    if not _cache:
        return []
    return random.sample(_cache, min(n, len(_cache)))


def get_headlines_for_agent(snap: dict, n: int = 3) -> list[dict]:
    """Return n headlines sampled uniformly from the cache."""
    _refresh_if_stale()
    if not _cache:
        return []
    return random.sample(_cache, min(n, len(_cache)))
