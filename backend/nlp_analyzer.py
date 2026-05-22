"""Background NLP enrichment for posts and news headlines.

Two daemon threads poll the database for unanalyzed rows and score them
via the Hugging Face Inference API (sentiment + emotion in two batched calls
per cycle, regardless of batch size). Disabled when HF_API_KEY is unset.
"""
import logging
import threading
import time

import requests

from config import Config
from database import db
from models import NewsItem, Post

logger = logging.getLogger(__name__)


_HF_SENTIMENT_URL = "https://router.huggingface.co/hf-inference/models/cardiffnlp/twitter-roberta-base-sentiment-latest"
_HF_EMOTION_URL   = "https://router.huggingface.co/hf-inference/models/j-hartmann/emotion-english-distilroberta-base"

_SENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}


def _hf_infer_batch(url, texts, headers, retries=6):
    """POST a batch of texts to a HF Inference API endpoint.
    Retries on any transient error (5xx, timeouts, model-loading error body)."""
    from requests.exceptions import ConnectionError as ReqConnError, ReadTimeout, Timeout
    for attempt in range(retries):
        backoff = min(20 * (attempt + 1), 60)
        try:
            resp = requests.post(url, json={"inputs": texts}, headers=headers, timeout=30)
        except (ReadTimeout, Timeout, ReqConnError) as exc:
            logger.warning("HF request error (attempt %d/%d) — retrying in %ds: %s",
                           attempt + 1, retries, backoff, exc)
            time.sleep(backoff)
            continue
        if resp.status_code in (500, 502, 503, 504):
            logger.warning("HF HTTP %d (attempt %d/%d) — retrying in %ds",
                           resp.status_code, attempt + 1, retries, backoff)
            time.sleep(backoff)
            continue
        resp.raise_for_status()
        result = resp.json()
        # HF sometimes returns 200 with {"error": "..."} while the model warms up
        if isinstance(result, dict) and "error" in result:
            logger.warning("HF error body (attempt %d/%d) — retrying in %ds: %s",
                           attempt + 1, retries, backoff, result["error"])
            time.sleep(backoff)
            continue
        return result
    raise RuntimeError(f"HF inference failed after {retries} attempts")


def _score_texts(texts):
    """Score a batch of texts. Returns list[(sentiment_float, emotion_label)] or None on failure.
    Two API calls total — sentiment + emotion — regardless of batch size."""
    key = Config.HF_API_KEY
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        sent_results = _hf_infer_batch(_HF_SENTIMENT_URL, texts, headers)
        emo_results  = _hf_infer_batch(_HF_EMOTION_URL,   texts, headers)
    except Exception:
        logger.exception("HF batch analysis failed")
        return None

    # The serverless API packs all per-input top labels into a single inner list:
    # [[result_input0, result_input1, ...]] — so we index via [0][i].
    out = []
    for i in range(len(texts)):
        sent = sent_results[0][i]
        emo  = emo_results[0][i]
        sentiment = round(_SENT_SCORE.get(sent["label"].lower(), 0.0), 4)
        emotion   = emo["label"].lower()
        out.append((sentiment, emotion))
    return out


def _analyze_news_batch(items, app):
    """Analyze a batch of (item_id, title, summary) tuples and persist results."""
    texts = [
        f"{title}. {summary}".strip() if summary else title
        for _, title, summary in items
    ]
    scored = _score_texts(texts)
    if scored is None:
        return

    with app.app_context():
        for i, (item_id, title, _) in enumerate(items):
            sentiment, emotion = scored[i]
            item = db.session.get(NewsItem, item_id)
            if item:
                item.sentiment = sentiment
                item.emotion   = emotion
                item.analyzed  = True
                logger.info("news analyzed — %s → sentiment:%.2f emotion:%s",
                            title[:50], sentiment, emotion)
        db.session.commit()


def _analyze_post_batch(post_ids_and_texts, app):
    """Analyze a batch of (post_id, content) tuples and persist results."""
    texts = [content for _, content in post_ids_and_texts]
    scored = _score_texts(texts)
    if scored is None:
        return

    with app.app_context():
        for i, (post_id, _) in enumerate(post_ids_and_texts):
            sentiment, emotion = scored[i]
            post = db.session.get(Post, post_id)
            if post:
                post.sentiment    = sentiment
                post.emotion      = emotion
                post.nlp_analyzed = True
        db.session.commit()
    logger.info("post NLP batch done — %d posts analyzed", len(post_ids_and_texts))


def start_post_analyzer(app):
    """Background thread: analyze unanalyzed public posts via HF Inference API."""
    if not Config.HF_API_KEY:
        return

    def loop():
        while True:
            time.sleep(45)
            with app.app_context():
                unanalyzed = (
                    Post.query
                    .filter_by(nlp_analyzed=False, is_public=True)
                    .filter(Post.parent_id.is_(None))  # top-level posts only
                    .order_by(Post.id)
                    .limit(10)
                    .all()
                )
                batch = [(p.id, p.content) for p in unanalyzed]
            if batch:
                _analyze_post_batch(batch, app)

    threading.Thread(target=loop, daemon=True).start()


def start_news_analyzer(app):
    """Background thread: analyze unanalyzed news items via HF Inference API."""
    if not Config.HF_API_KEY:
        logger.info("HF_API_KEY not set — news sentiment analysis disabled")
        return

    def loop():
        while True:
            time.sleep(30)
            with app.app_context():
                unanalyzed = NewsItem.query.filter_by(analyzed=False).limit(5).all()
                items = [(i.id, i.title, i.summary) for i in unanalyzed]
            if items:
                _analyze_news_batch(items, app)

    threading.Thread(target=loop, daemon=True).start()
