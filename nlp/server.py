"""
NLP microservice — sentiment + emotion analysis.
Runs on port 5001, independent of the Flask backend.

Models:
  - cardiffnlp/twitter-roberta-base-sentiment-latest  (sentiment)
  - j-hartmann/emotion-english-distilroberta-base     (emotion)

Usage:
  POST /analyze
  Body: {"text": "any string"}
  Returns: {"sentiment": {"label": str, "score": float}, "emotion": {"label": str, "scores": {...}}}

  POST /analyze/batch
  Body: {"texts": ["string", ...]}
  Returns: list of the above
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from transformers import pipeline

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ── Model handles (loaded at startup) ────────────────────────────────────────
_sentiment_pipe = None
_emotion_pipe   = None

SENTIMENT_MODEL = "cardiffnlp/twitter-roberta-base-sentiment-latest"
EMOTION_MODEL   = "j-hartmann/emotion-english-distilroberta-base"

# Map Cardiff model labels to a clean -1→1 score
_SENTIMENT_SCORE = {
    "positive":  1.0,
    "neutral":   0.0,
    "negative": -1.0,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _sentiment_pipe, _emotion_pipe
    logger.info("loading sentiment model: %s", SENTIMENT_MODEL)
    _sentiment_pipe = pipeline(
        "text-classification",
        model=SENTIMENT_MODEL,
        top_k=None,
        truncation=True,
        max_length=512,
    )
    logger.info("loading emotion model: %s", EMOTION_MODEL)
    _emotion_pipe = pipeline(
        "text-classification",
        model=EMOTION_MODEL,
        top_k=None,
        truncation=True,
        max_length=512,
    )
    logger.info("models ready")
    yield


app = FastAPI(title="NLP Service", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    text: str

class BatchRequest(BaseModel):
    texts: list[str]


# ── Core analysis ─────────────────────────────────────────────────────────────

def _analyze_one(text: str) -> dict[str, Any]:
    text = text.strip()
    if not text:
        raise ValueError("empty text")

    # Sentiment
    sent_results = _sentiment_pipe(text)[0]
    sent_by_label = {r["label"].lower(): r["score"] for r in sent_results}
    top_sent = max(sent_by_label, key=sent_by_label.get)
    # Weighted score: positive pulls toward +1, negative toward -1
    score = (
        sent_by_label.get("positive", 0) * 1.0
        + sent_by_label.get("neutral",  0) * 0.0
        + sent_by_label.get("negative", 0) * -1.0
    )

    # Emotion
    emo_results = _emotion_pipe(text)[0]
    emo_scores  = {r["label"].lower(): round(r["score"], 4) for r in emo_results}
    top_emo     = max(emo_scores, key=emo_scores.get)

    return {
        "sentiment": {
            "label":  top_sent,
            "score":  round(score, 4),
            "scores": {k: round(v, 4) for k, v in sent_by_label.items()},
        },
        "emotion": {
            "label":  top_emo,
            "scores": emo_scores,
        },
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {"ok": True, "models_loaded": _sentiment_pipe is not None}


@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    try:
        return _analyze_one(req.text)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/analyze/batch")
def analyze_batch(req: BatchRequest):
    if len(req.texts) > 100:
        raise HTTPException(status_code=400, detail="max 100 texts per batch")
    return [_analyze_one(t) for t in req.texts]


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=5001, reload=False)
