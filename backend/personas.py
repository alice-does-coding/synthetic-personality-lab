"""
Persona archetype loader.

At import time, scans ``seed/personas/*.json`` and builds the ``PERSONAS`` dict
that the rest of the codebase reads. Each JSON file is one archetype:

  {
    "key":         "doomscroller",
    "label":       "Doomscroller",
    "description": "Addicted to catastrophic news...",
    "bio_prompt":  "This entity is addicted to ...",          # null for Pokemon
    "priors": {
      "openness":          [55, 12],                          # [mean, std], 0-100
      "conscientiousness": [35, 12],
      ...
    },
    "name_pool": ["Bulbasaur", ...]                           # optional
  }

Drop a new JSON file in ``seed/personas/`` to add an archetype; remove one to
drop it. The ``key`` field is the persona identifier used in API calls and the
``persona`` column on the ``runs`` table.

Personas with a ``name_pool`` (e.g. Greek pantheon, Pokédex lists) pin the
seeded ``agent_count`` to the length of the pool so each name lands on
exactly one agent.
"""

import json
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# seed/ lives at the repo root, one level up from backend/
_REPO_ROOT  = Path(__file__).resolve().parent.parent
_PERSONA_DIR = _REPO_ROOT / "seed" / "personas"


def _load_personas():
    if not _PERSONA_DIR.is_dir():
        logger.warning("persona directory not found: %s", _PERSONA_DIR)
        return {}
    personas = {}
    for path in sorted(_PERSONA_DIR.glob("*.json")):
        try:
            with path.open() as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("failed to load persona %s: %s", path.name, exc)
            continue
        key = data.get("key") or path.stem
        # Normalise priors from [mean, std] lists into the (mean, std) tuples the
        # downstream sampling code already expects.
        priors = {trait: tuple(values) for trait, values in data.get("priors", {}).items()}
        personas[key] = {
            "label":       data.get("label", key),
            "description": data.get("description", ""),
            "bio_prompt":  data.get("bio_prompt"),
            "priors":      priors,
            "name_pool":   data.get("name_pool"),    # optional list[str]
            "bio_framing": data.get("bio_framing"),  # optional str template (uses {name})
        }
    return personas


PERSONAS = _load_personas()
