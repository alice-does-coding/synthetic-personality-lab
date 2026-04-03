"""Quick smoke test for the HF Inference API integration.

Usage:
    cd backend && python test_hf.py

Requires HF_API_KEY in backend/.env (or the environment).
"""

import sys
from dotenv import load_dotenv
load_dotenv()

from config import Config
from simulation import _hf_infer_batch, _HF_SENTIMENT_URL, _HF_EMOTION_URL

HEADLINES = [
    "Scientists discover new species of deep-sea fish",
    "Stock markets tumble amid recession fears",
    "Local community rallies to support flood victims",
    "Tech giant announces record profits",
    "Climate report warns of accelerating ice melt",
]

if not Config.HF_API_KEY:
    print("ERROR: HF_API_KEY not set — add it to backend/.env")
    sys.exit(1)

headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {Config.HF_API_KEY}",
}

print(f"Testing batch of {len(HEADLINES)} headlines...\n")

_SENT_SCORE = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}

print("── Sentiment ──────────────────────────────────────────")
sent_results = _hf_infer_batch(_HF_SENTIMENT_URL, HEADLINES, headers)
for i, headline in enumerate(HEADLINES):
    r = sent_results[0][i]
    score = _SENT_SCORE.get(r["label"].lower(), 0.0)
    print(f"  {score:+.1f}  [{r['label']:<8}]  {headline}")

print("\n── Emotion ────────────────────────────────────────────")
emo_results = _hf_infer_batch(_HF_EMOTION_URL, HEADLINES, headers)
for i, headline in enumerate(HEADLINES):
    r = emo_results[0][i]
    print(f"  {r['label']:<12} ({r['score']:.2f})  {headline}")

print("\nOK — both models responded correctly.")
