"""
Lurkr corpus analysis — paper-ready figures.

Usage:
    # Single run: OCEAN trajectories, word cloud, vocabulary comparison
    python corpus_analysis.py --run 6

    # H2 comparison: drift comparison, agent trajectories, vocabulary diff
    python corpus_analysis.py --compare 6 7

Output: corpus_output/run_<id>/ or corpus_output/compare_<id1>_vs_<id2>/

Reads DATABASE_URL from environment (set in .env). Works with SQLite locally
or Postgres in production.
"""

import argparse
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── Palette (matches Lurkr UI) ────────────────────────────────────────────────

TRAIT_COLORS = {
    "openness":          "#c77dff",   # purple
    "conscientiousness": "#2dd4bf",   # mint
    "extraversion":      "#fb7185",   # rose
    "agreeableness":     "#a78bfa",   # lavender
    "neuroticism":       "#ff3ea5",   # pink
}
TRAITS = list(TRAIT_COLORS)
TRAIT_LABELS = {
    "openness":          "Openness",
    "conscientiousness": "Conscientiousness",
    "extraversion":      "Extraversion",
    "agreeableness":     "Agreeableness",
    "neuroticism":       "Neuroticism",
}

GROUNDED_COLOR   = "#2dd4bf"   # teal — treatment
UNGROUNDED_COLOR = "#ff3ea5"   # pink — control

STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "is", "it", "its", "as", "that", "this",
    "are", "was", "be", "been", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "not", "no", "so",
    "we", "they", "he", "she", "i", "you", "my", "your", "our", "their",
    "what", "who", "how", "when", "where", "if", "just", "more", "like",
    "than", "then", "there", "here", "can", "all", "one", "into", "out",
    "up", "about", "over", "after", "while", "every", "even", "still",
    "each", "through", "only", "also", "very", "much", "some", "any",
    "s", "t", "re", "ll", "ve", "m", "d",
    "doesn", "isn", "wasn", "aren", "weren", "couldn", "wouldn", "shouldn",
    "hadn", "hasn", "haven", "didn", "don", "won",
}

# ── Matplotlib style ──────────────────────────────────────────────────────────

def apply_style():
    plt.rcParams.update({
        "figure.facecolor":     "#000000",
        "axes.facecolor":       "#000000",
        "axes.edgecolor":       "#333333",
        "axes.labelcolor":      "#cccccc",
        "axes.titlecolor":      "#ffffff",
        "xtick.color":          "#888888",
        "ytick.color":          "#888888",
        "text.color":           "#cccccc",
        "grid.color":           "#1e1e1e",
        "grid.linewidth":       0.6,
        "legend.facecolor":     "#0a0a0a",
        "legend.edgecolor":     "#333333",
        "legend.labelcolor":    "#cccccc",
        "font.family":          "monospace",
        "axes.spines.top":      False,
        "axes.spines.right":    False,
    })

# ── DB helpers (via Flask / SQLAlchemy) ───────────────────────────────────────

def get_app():
    from app import create_app
    return create_app()


def fetch_snapshots(run_id):
    """Return list of dicts: {tick_number, agent_id, name, O, C, E, A, N}"""
    from models import PersonalitySnapshot, Agent
    from database import db
    rows = (
        db.session.query(PersonalitySnapshot, Agent.name)
        .join(Agent, Agent.id == PersonalitySnapshot.agent_id)
        .filter(PersonalitySnapshot.run_id == run_id)
        .order_by(PersonalitySnapshot.tick_number)
        .all()
    )
    return [
        {
            "tick":    s.tick_number,
            "agent_id": s.agent_id,
            "name":    name,
            "O": s.openness,
            "C": s.conscientiousness,
            "E": s.extraversion,
            "A": s.agreeableness,
            "N": s.neuroticism,
        }
        for s, name in rows
    ]


def fetch_posts(run_id):
    """Return list of dicts with post content and author's current OCEAN scores."""
    from models import Post, Agent
    from database import db
    rows = (
        db.session.query(Post, Agent)
        .join(Agent, Agent.id == Post.agent_id)
        .filter(Post.run_id == run_id, Post.content.isnot(None))
        .order_by(Post.tick_number)
        .all()
    )
    return [
        {
            "content":     p.content,
            "tick":        p.tick_number,
            "handle":      a.handle,
            "name":        a.name,
            "O": a.openness, "C": a.conscientiousness,
            "E": a.extraversion, "A": a.agreeableness, "N": a.neuroticism,
        }
        for p, a in rows
    ]


def fetch_run(run_id):
    from models import Run
    return Run.query.get_or_404(run_id)


# ── Text helpers ──────────────────────────────────────────────────────────────

def tokenize(text):
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]


def bigrams(tokens):
    return [f"{tokens[i]} {tokens[i+1]}" for i in range(len(tokens) - 1)]


def dominant_trait(row):
    scores = {t: row[t[0].upper()] or 0 for t in TRAITS}
    return max(scores, key=scores.get)


# ── Mean trajectories ─────────────────────────────────────────────────────────

def mean_trajectories(snapshots):
    """
    Returns dict: {tick -> {trait -> mean_score}},
    and dict: {tick -> {trait -> std_score}}
    """
    from collections import defaultdict
    by_tick = defaultdict(lambda: defaultdict(list))
    for s in snapshots:
        for t, key in [("openness","O"),("conscientiousness","C"),("extraversion","E"),("agreeableness","A"),("neuroticism","N")]:
            if s[key] is not None:
                by_tick[s["tick"]][t].append(s[key])
    ticks = sorted(by_tick)
    means = {tick: {t: np.mean(vals) for t, vals in by_tick[tick].items()} for tick in ticks}
    stds  = {tick: {t: np.std(vals)  for t, vals in by_tick[tick].items()} for tick in ticks}
    return ticks, means, stds


# ── Chart 1: OCEAN mean trajectories (single run) ────────────────────────────

def plot_ocean_trajectories(snapshots, run, outdir):
    ticks, means, stds = mean_trajectories(snapshots)
    xs = np.array(ticks)

    fig, ax = plt.subplots(figsize=(12, 6))
    fig.patch.set_facecolor("#000000")

    for trait in TRAITS:
        ys  = np.array([means[t][trait] for t in ticks])
        sds = np.array([stds[t][trait]  for t in ticks])
        color = TRAIT_COLORS[trait]
        ax.plot(xs, ys, color=color, linewidth=2, label=TRAIT_LABELS[trait])
        ax.fill_between(xs, ys - sds, ys + sds, color=color, alpha=0.08)

    ax.set_xlabel("tick", fontsize=10)
    ax.set_ylabel("mean score (± 1 SD)", fontsize=10)
    ax.set_title(f"OCEAN TRAJECTORIES — {run.name.upper()}", fontsize=12, pad=14)
    ax.set_ylim(0, 105)
    ax.axhline(50, color="#333333", linewidth=0.5, linestyle="--")
    ax.grid(True, axis="y")
    ax.legend(loc="upper right", fontsize=9, ncol=2)

    fig.tight_layout()
    path = outdir / "ocean_trajectories.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Chart 2: H2 drift comparison (two runs) ───────────────────────────────────

def plot_h2_comparison(snaps_a, snaps_b, run_a, run_b, outdir):
    """
    5-panel figure. Each panel = one trait. Two lines: grounded vs ungrounded.
    Y axis = delta from tick-0 baseline (Δscore), so the shared starting point is always 0.
    """
    ticks_a, means_a, _ = mean_trajectories(snaps_a)
    ticks_b, means_b, _ = mean_trajectories(snaps_b)

    # Baseline at tick 0
    base_a = means_a.get(0, {})
    base_b = means_b.get(0, {})

    label_a = "grounded (treatment)"   if run_a.ipip_grounded else "ungrounded (control)"
    label_b = "ungrounded (control)"   if not run_b.ipip_grounded else "grounded (treatment)"
    color_a = GROUNDED_COLOR   if run_a.ipip_grounded else UNGROUNDED_COLOR
    color_b = UNGROUNDED_COLOR if run_a.ipip_grounded else GROUNDED_COLOR

    fig, axes = plt.subplots(1, 5, figsize=(20, 5), sharey=False)
    fig.patch.set_facecolor("#000000")
    fig.suptitle(
        f"H2 EXPERIMENT — GROUNDED vs UNGROUNDED IPIP\n"
        f"{run_a.name}  ·  {run_b.name}  ·  seed {run_a.random_seed}  ·  {len(ticks_a)} assessment cycles",
        fontsize=11, y=1.02, color="#ffffff",
    )

    for ax, trait in zip(axes, TRAITS):
        xs_a = np.array(ticks_a)
        xs_b = np.array(ticks_b)
        ys_a = np.array([means_a[t][trait] - base_a.get(trait, 0) for t in ticks_a])
        ys_b = np.array([means_b[t][trait] - base_b.get(trait, 0) for t in ticks_b])

        ax.axhline(0, color="#444444", linewidth=0.8, linestyle="--")
        ax.plot(xs_a, ys_a, color=color_a, linewidth=2, label=label_a)
        ax.plot(xs_b, ys_b, color=color_b, linewidth=2, label=label_b)

        ax.set_title(TRAIT_LABELS[trait], fontsize=10, color=TRAIT_COLORS[trait], pad=8)
        ax.set_xlabel("tick", fontsize=8)
        if ax is axes[0]:
            ax.set_ylabel("Δ score from baseline", fontsize=8)
        ax.grid(True, axis="y")
        ax.tick_params(labelsize=8)

    # Shared legend below
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=2, fontsize=9,
               bbox_to_anchor=(0.5, -0.06), framealpha=0.8)

    fig.tight_layout()
    path = outdir / "h2_drift_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Chart 3: Agent-level E trajectories (compare mode) ───────────────────────

def plot_agent_extraversion(snaps_a, snaps_b, run_a, run_b, outdir):
    """
    Two panels side by side. Each agent = one thin line. Population mean = thick line.
    Shows individual variation in E drift within each condition.
    """
    from collections import defaultdict

    def by_agent(snapshots):
        d = defaultdict(list)
        for s in snapshots:
            d[s["name"]].append((s["tick"], s["E"]))
        return {name: sorted(pts) for name, pts in d.items()}

    agents_a = by_agent(snaps_a)
    agents_b = by_agent(snaps_b)
    ticks_a, means_a, _ = mean_trajectories(snaps_a)
    ticks_b, means_b, _ = mean_trajectories(snaps_b)

    label_a = "grounded" if run_a.ipip_grounded else "ungrounded"
    label_b = "ungrounded" if run_a.ipip_grounded else "grounded"
    color_a = GROUNDED_COLOR if run_a.ipip_grounded else UNGROUNDED_COLOR
    color_b = UNGROUNDED_COLOR if run_a.ipip_grounded else GROUNDED_COLOR

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(16, 7), sharey=True)
    fig.patch.set_facecolor("#000000")
    fig.suptitle("EXTRAVERSION DRIFT — AGENT-LEVEL TRAJECTORIES", fontsize=12, y=1.01, color="#ffffff")

    for ax, agents, ticks, means, color, label in [
        (ax_a, agents_a, ticks_a, means_a, color_a, label_a),
        (ax_b, agents_b, ticks_b, means_b, color_b, label_b),
    ]:
        for pts in agents.values():
            xs, ys = zip(*pts)
            ax.plot(xs, ys, color=color, linewidth=0.4, alpha=0.2)

        # Population mean
        mean_e = [means[t]["extraversion"] for t in ticks]
        ax.plot(ticks, mean_e, color=color, linewidth=2.5, label=f"mean ({label})", zorder=5)

        ax.axhline(50, color="#333333", linewidth=0.5, linestyle="--")
        ax.set_ylim(0, 105)
        ax.set_xlabel("tick", fontsize=10)
        ax.set_ylabel("extraversion score", fontsize=10)
        ax.set_title(label.upper(), fontsize=11, color=color, pad=10)
        ax.grid(True, axis="y")
        ax.legend(fontsize=9)

    fig.tight_layout()
    path = outdir / "h2_extraversion_agents.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Chart 4: Word cloud ───────────────────────────────────────────────────────

def plot_wordcloud(posts, run, outdir):
    try:
        from wordcloud import WordCloud
    except ImportError:
        print("  wordcloud not installed — skipping word cloud")
        return

    word_freq = Counter()
    word_trait_votes = defaultdict(Counter)

    for p in posts:
        tokens = tokenize(p["content"])
        trait = dominant_trait(p)
        for w in tokens:
            word_freq[w] += 1
            word_trait_votes[w][trait] += 1

    def color_func(word, **kwargs):
        votes = word_trait_votes.get(word, {})
        if not votes:
            return "#ffffff"
        return TRAIT_COLORS[max(votes, key=votes.get)]

    wc = WordCloud(
        width=1600, height=800,
        background_color="#000000",
        max_words=200,
        color_func=color_func,
        prefer_horizontal=0.8,
    ).generate_from_frequencies(word_freq)

    fig, ax = plt.subplots(figsize=(16, 8), facecolor="#000000")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")

    for trait, color in TRAIT_COLORS.items():
        ax.plot([], [], "s", color=color, label=TRAIT_LABELS[trait], markersize=9)
    ax.legend(loc="lower right", fontsize=9, framealpha=0.8)
    ax.set_title(
        f"POST CORPUS — WORD CLOUD  ·  {run.name.upper()}  ·  {len(posts)} posts",
        color="white", fontsize=12, pad=12,
    )

    fig.tight_layout()
    path = outdir / "wordcloud.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Chart 5: Vocabulary comparison high-N vs low-N (single run) ──────────────

def plot_vocab_comparison(posts, run, outdir):
    high_n = Counter(); low_n = Counter()
    high_bi = Counter(); low_bi = Counter()

    for p in posts:
        tokens = tokenize(p["content"])
        bis = bigrams(tokens)
        n = p["N"] or 0
        if n >= 65:
            high_n.update(tokens); high_bi.update(bis)
        elif n <= 50:
            low_n.update(tokens);  low_bi.update(bis)

    def top_combined(uni, bi, n=30):
        combined = Counter(uni)
        combined.update({k: v for k, v in bi.items() if v >= 3})
        return combined.most_common(n)

    high_top = top_combined(high_n, high_bi)
    low_top  = top_combined(low_n,  low_bi)

    fig, (ax_h, ax_l) = plt.subplots(1, 2, figsize=(18, 10), facecolor="#000000")
    fig.suptitle(
        f"VOCABULARY COMPARISON — HIGH-N vs LOW-N  ·  {run.name.upper()}",
        color="white", fontsize=13, y=1.01,
    )

    def draw(ax, data, color, title):
        if not data:
            ax.text(0.5, 0.5, "no data", ha="center", va="center", transform=ax.transAxes)
            return
        words, counts = zip(*data)
        y = range(len(words))
        ax.barh(y, counts, color=color, height=0.7)
        ax.set_yticks(y)
        ax.set_yticklabels(words, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=11, pad=10)
        ax.grid(True, axis="x")

    draw(ax_h, high_top, TRAIT_COLORS["neuroticism"],       f"HIGH NEUROTICISM (≥65)\ntop 30 terms")
    draw(ax_l, low_top,  TRAIT_COLORS["conscientiousness"], f"LOW NEUROTICISM (≤50)\ntop 30 terms")

    fig.tight_layout()
    path = outdir / "vocab_comparison.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Chart 6: Vocabulary diff between two runs ─────────────────────────────────

def plot_vocab_diff(posts_a, posts_b, run_a, run_b, outdir):
    """
    Words that appear disproportionately in grounded vs ungrounded corpus.
    Log-odds ratio — highlights what the grounded condition generates differently.
    """
    freq_a = Counter(w for p in posts_a for w in tokenize(p["content"]))
    freq_b = Counter(w for p in posts_b for w in tokenize(p["content"]))

    total_a = sum(freq_a.values()) or 1
    total_b = sum(freq_b.values()) or 1
    vocab = set(freq_a) | set(freq_b)

    # Log-odds with Laplace smoothing
    log_odds = {}
    for w in vocab:
        pa = (freq_a.get(w, 0) + 1) / (total_a + len(vocab))
        pb = (freq_b.get(w, 0) + 1) / (total_b + len(vocab))
        log_odds[w] = np.log(pa / pb)

    sorted_words = sorted(log_odds, key=log_odds.get)
    top_b = sorted_words[:20]    # more in run_b (ungrounded)
    top_a = sorted_words[-20:]   # more in run_a (grounded)
    top_a.reverse()

    label_a = "grounded" if run_a.ipip_grounded else "ungrounded"
    label_b = "ungrounded" if run_a.ipip_grounded else "grounded"
    color_a = GROUNDED_COLOR if run_a.ipip_grounded else UNGROUNDED_COLOR
    color_b = UNGROUNDED_COLOR if run_a.ipip_grounded else GROUNDED_COLOR

    fig, (ax_a, ax_b) = plt.subplots(1, 2, figsize=(16, 8), facecolor="#000000")
    fig.suptitle(
        f"VOCABULARY DIVERGENCE — {label_a.upper()} vs {label_b.upper()}\n"
        f"log-odds ratio (higher = more characteristic of that condition)",
        color="white", fontsize=12, y=1.02,
    )

    def draw(ax, words, color, title):
        vals = [log_odds[w] for w in words]
        y = range(len(words))
        ax.barh(y, [abs(v) for v in vals], color=color, height=0.7)
        ax.set_yticks(y)
        ax.set_yticklabels(words, fontsize=9)
        ax.invert_yaxis()
        ax.set_title(title, fontsize=10, pad=10, color=color)
        ax.set_xlabel("log-odds (abs)", fontsize=8)
        ax.grid(True, axis="x")

    draw(ax_a, top_a, color_a, f"more in {label_a}")
    draw(ax_b, top_b, color_b, f"more in {label_b}")

    fig.tight_layout()
    path = outdir / "vocab_divergence.png"
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print(f"  saved {path}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Lurkr corpus analysis — paper-ready figures")
    group  = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--run",     type=int, metavar="RUN_ID",
                       help="single run analysis")
    group.add_argument("--compare", type=int, nargs=2, metavar=("RUN_A", "RUN_B"),
                       help="H2 comparison between two matched runs")
    args = parser.parse_args()

    apply_style()
    app = get_app()

    with app.app_context():
        if args.run:
            run_id = args.run
            run = fetch_run(run_id)
            outdir = Path("corpus_output") / f"run_{run_id}"
            outdir.mkdir(parents=True, exist_ok=True)
            print(f"\nRun {run_id}: {run.name}  ({run.status}, tick {run.last_tick})")

            print("\nFetching data...")
            snapshots = fetch_snapshots(run_id)
            posts     = fetch_posts(run_id)
            print(f"  {len(snapshots)} snapshots, {len(posts)} posts")

            print("\nGenerating figures...")
            plot_ocean_trajectories(snapshots, run, outdir)
            plot_wordcloud(posts, run, outdir)
            plot_vocab_comparison(posts, run, outdir)

            print(f"\nDone. Output: {outdir}/")

        else:
            id_a, id_b = args.compare
            outdir = Path("corpus_output") / f"compare_{id_a}_vs_{id_b}"
            outdir.mkdir(parents=True, exist_ok=True)

            run_a = fetch_run(id_a)
            run_b = fetch_run(id_b)
            print(f"\nRun {id_a}: {run_a.name}  (grounded={run_a.ipip_grounded}, seed={run_a.random_seed})")
            print(f"Run {id_b}: {run_b.name}  (grounded={run_b.ipip_grounded}, seed={run_b.random_seed})")

            if run_a.random_seed != run_b.random_seed:
                print("WARNING: runs have different random seeds — not a matched pair")

            print("\nFetching data...")
            snaps_a  = fetch_snapshots(id_a)
            snaps_b  = fetch_snapshots(id_b)
            posts_a  = fetch_posts(id_a)
            posts_b  = fetch_posts(id_b)
            print(f"  Run {id_a}: {len(snaps_a)} snapshots, {len(posts_a)} posts")
            print(f"  Run {id_b}: {len(snaps_b)} snapshots, {len(posts_b)} posts")

            print("\nGenerating figures...")
            plot_h2_comparison(snaps_a, snaps_b, run_a, run_b, outdir)
            plot_agent_extraversion(snaps_a, snaps_b, run_a, run_b, outdir)
            plot_vocab_diff(posts_a, posts_b, run_a, run_b, outdir)

            print(f"\nDone. Output: {outdir}/")


if __name__ == "__main__":
    main()
