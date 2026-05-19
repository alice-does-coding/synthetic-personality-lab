"""
Seed the public-simulation run from a JSON seed file.

The seed file is a list of agent records — each with a name, handle, bio, and
the five OCEAN scores on a 0–100 scale. Example::

    {
      "name":        "Optional descriptive name for the population",
      "description": "Optional one-line description",
      "agents": [
        {
          "name":              "Cassandra",
          "handle":            "cassandra_warns",
          "bio":               "i told them.",
          "openness":          85,
          "conscientiousness": 70,
          "extraversion":      60,
          "agreeableness":     50,
          "neuroticism":       90
        }
      ]
    }

Top-level ``agents`` is required; ``name`` and ``description`` are advisory.

Usage:

    SEED_POPULATION_PATH=path/to/seed.json python3 seed_simulation.py
    # or
    python3 seed_simulation.py path/to/seed.json

No default file ships with the repo — bring your own population.
"""

import json
import os
import sys
from pathlib import Path


def _seed_token(i):
    return f"00000000-seed-0000-0000-{i:012d}"


def _resolve_seed_path():
    """Pick a seed file path from CLI args first, then SEED_POPULATION_PATH."""
    if len(sys.argv) > 1:
        return Path(sys.argv[1]).expanduser().resolve()
    env_path = os.environ.get("SEED_POPULATION_PATH")
    if env_path:
        return Path(env_path).expanduser().resolve()
    return None


def _load_population(path):
    with path.open() as f:
        data = json.load(f)
    if isinstance(data, list):
        # Bare list of agents is also accepted.
        return data
    agents = data.get("agents")
    if not isinstance(agents, list):
        raise ValueError(
            f"{path}: expected a top-level 'agents' array or a bare list of agents."
        )
    return agents


def _print_usage_and_exit():
    print(
        "seed_simulation.py: no seed file provided.\n"
        "\n"
        "Bring your own population:\n"
        "  SEED_POPULATION_PATH=path/to/seed.json python3 seed_simulation.py\n"
        "  python3 seed_simulation.py path/to/seed.json\n"
        "\n"
        "See the 'Run your own simulation' section in the README for the schema.",
        file=sys.stderr,
    )
    sys.exit(2)


def seed():
    path = _resolve_seed_path()
    if path is None:
        _print_usage_and_exit()
    if not path.is_file():
        print(f"seed file not found: {path}", file=sys.stderr)
        sys.exit(2)

    agents = _load_population(path)
    if not agents:
        print(f"{path}: no agents to seed.", file=sys.stderr)
        sys.exit(2)

    # Deferred imports: bringing flask + SQLAlchemy in only after we've
    # validated the seed file so `python seed_simulation.py` with no args
    # can print usage even before deps are installed.
    from app import create_app
    from simulation import create_agent

    app = create_app()
    with app.app_context():
        total = len(agents)
        for i, spec in enumerate(agents, 1):
            try:
                agent = create_agent(
                    _seed_token(i),
                    seed_mode="scratch",
                    name=spec["name"],
                    bio=spec.get("bio", ""),
                    openness=spec["openness"],
                    conscientiousness=spec["conscientiousness"],
                    extraversion=spec["extraversion"],
                    agreeableness=spec["agreeableness"],
                    neuroticism=spec["neuroticism"],
                )
                print(f"[{i:02d}/{total}] ✓ @{agent.handle} — {agent.name}")
            except Exception as exc:
                handle = spec.get("handle", spec.get("name", "?"))
                print(f"[{i:02d}/{total}] ✗ {handle} — {exc}")


if __name__ == "__main__":
    seed()
