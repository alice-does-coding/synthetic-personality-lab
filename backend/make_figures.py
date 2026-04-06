"""
Generate paper figures from local lab.db (NGE run) and prod export if available.
Outputs to ../figures/ directory.
"""
import sqlite3
import os
import math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

DB = os.path.join(os.path.dirname(__file__), "instance", "lab.db")
OUT = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT, exist_ok=True)

TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
TRAIT_LABELS = ["Openness", "Conscientiousness", "Extraversion", "Agreeableness", "Neuroticism"]
TRAIT_COLORS = ["#4C72B0", "#55A868", "#C44E52", "#8172B2", "#CCB974"]

ATTRACTOR = {"openness": 60, "conscientiousness": 60, "extraversion": 65, "agreeableness": 58, "neuroticism": 47}

# ── Style ──────────────────────────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "serif",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 150,
})

def load_nge(db=DB, run_id=1):
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    agents = {r["id"]: dict(r) for r in cur.execute(
        "SELECT id, name FROM agents WHERE run_id=?", (run_id,)).fetchall()}

    snaps = cur.execute(
        "SELECT agent_id, tick_number, openness, conscientiousness, extraversion, "
        "agreeableness, neuroticism FROM personality_snapshots WHERE run_id=? "
        "ORDER BY tick_number", (run_id,)).fetchall()

    posts = cur.execute(
        "SELECT agent_id, sentiment FROM posts WHERE run_id=? AND sentiment IS NOT NULL",
        (run_id,)).fetchall()

    follows = cur.execute(
        "SELECT followee_id, COUNT(*) as n FROM follows "
        "JOIN agents a ON follows.follower_id = a.id WHERE a.run_id=? "
        "GROUP BY followee_id", (run_id,)).fetchall()

    con.close()
    return agents, snaps, posts, follows


# ── Figure 2: NGE Population Mean Trajectories ────────────────────────────────
def fig2_nge_convergence(agents, snaps):
    by_tick = defaultdict(list)
    for s in snaps:
        by_tick[s["tick_number"]].append(s)

    ticks = sorted(by_tick.keys())
    fig, axes = plt.subplots(1, 5, figsize=(14, 3.2), sharey=False)
    fig.suptitle("Population-Level OCEAN Convergence (NGE Run, N=17)", fontsize=12, y=1.02)

    for ax, trait, label, color, aval in zip(axes, TRAITS, TRAIT_LABELS, TRAIT_COLORS,
                                              [ATTRACTOR[t] for t in TRAITS]):
        means, sds = [], []
        for t in ticks:
            vals = [s[trait] for s in by_tick[t] if s[trait] is not None]
            m = sum(vals) / len(vals)
            sd = math.sqrt(sum((v - m) ** 2 for v in vals) / len(vals))
            means.append(m)
            sds.append(sd)

        means = np.array(means)
        sds = np.array(sds)

        ax.fill_between(ticks, means - sds, means + sds, alpha=0.15, color=color)
        ax.plot(ticks, means, color=color, lw=2)
        ax.axhline(aval, color=color, lw=1, ls="--", alpha=0.6)
        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Tick", fontsize=9)
        ax.set_ylim(0, 105)
        ax.set_xlim(0, max(ticks))
        if ax == axes[0]:
            ax.set_ylabel("Score (0–100)", fontsize=9)
        ax.annotate(f"T*≈{aval}", xy=(max(ticks), aval), xytext=(4, 2),
                    textcoords="offset points", fontsize=7, color=color, alpha=0.8)

    plt.tight_layout()
    path = os.path.join(OUT, "fig2_nge_convergence.pdf")
    plt.savefig(path, bbox_inches="tight")
    plt.savefig(path.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"Saved {path}")
    plt.close()


# ── Figure 3: Seed value vs. Δ(trait) — shows bidirectional attractor pull ────
def fig3_attractor_pull(agents, snaps):
    by_agent = defaultdict(dict)
    for s in snaps:
        by_agent[s["agent_id"]][s["tick_number"]] = s

    fig, axes = plt.subplots(1, 5, figsize=(14, 3.8), sharey=False, sharex=False)
    fig.suptitle("Attractor Pull: Seed Value vs. Δ Score (NGE Run, N=17)\n"
                 "Agents above T* are pulled down; agents below are pulled up.",
                 fontsize=11, y=1.04)

    for ax, trait, label, color, aval in zip(axes, TRAITS, TRAIT_LABELS, TRAIT_COLORS,
                                              [ATTRACTOR[t] for t in TRAITS]):
        seeds, deltas = [], []
        for aid, tdict in by_agent.items():
            if len(tdict) < 2:
                continue
            t0, tf = min(tdict), max(tdict)
            v0, vf = tdict[t0][trait], tdict[tf][trait]
            if v0 is None or vf is None:
                continue
            seeds.append(v0)
            deltas.append(vf - v0)

        seeds = np.array(seeds)
        deltas = np.array(deltas)

        ax.scatter(seeds, deltas, color=color, s=55, alpha=0.75, edgecolors="white",
                   lw=0.8, zorder=3)
        ax.axhline(0, color="black", lw=0.8, alpha=0.4)
        ax.axvline(aval, color="black", lw=1.2, ls="--", alpha=0.5)
        ax.annotate(f"T*={aval}", xy=(aval, ax.get_ylim()[0] if ax.get_ylim()[0] else -30),
                    xytext=(3, 4), textcoords="offset points", fontsize=8, alpha=0.7)

        # Trend line
        if len(seeds) > 2:
            z = np.polyfit(seeds, deltas, 1)
            p = np.poly1d(z)
            xs = np.linspace(seeds.min(), seeds.max(), 100)
            ax.plot(xs, p(xs), color=color, lw=1.5, alpha=0.5, ls="-")

        ax.set_title(label, fontsize=10)
        ax.set_xlabel("Seed value", fontsize=9)
        if ax == axes[0]:
            ax.set_ylabel("Δ Score (final − seed)", fontsize=9)
        ax.set_xlim(0, 105)

    plt.tight_layout()
    path = os.path.join(OUT, "fig3_attractor_pull.pdf")
    plt.savefig(path, bbox_inches="tight")
    plt.savefig(path.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"Saved {path}")
    plt.close()


# ── Figure 4: Sentiment × ΔN scatter (Ritsuko / H3 evidence) ─────────────────
def fig4_sentiment_neuroticism(agents, snaps, posts, follows):
    # Per-agent: mean sentiment, ΔN, follower count
    by_agent_snaps = defaultdict(list)
    for s in snaps:
        by_agent_snaps[s["agent_id"]].append(s)

    by_agent_posts = defaultdict(list)
    for p in posts:
        if p["sentiment"] is not None:
            by_agent_posts[p["agent_id"]].append(p["sentiment"])

    follower_count = {r["followee_id"]: r["n"] for r in follows}

    data = []
    for aid, slist in by_agent_snaps.items():
        slist_sorted = sorted(slist, key=lambda x: x["tick_number"])
        if len(slist_sorted) < 2:
            continue
        n0 = slist_sorted[0]["neuroticism"]
        nf = slist_sorted[-1]["neuroticism"]
        if n0 is None or nf is None:
            continue
        delta_n = nf - n0
        sentiments = by_agent_posts.get(aid, [])
        if not sentiments:
            continue
        mean_sent = sum(sentiments) / len(sentiments)
        k = follower_count.get(aid, 0)
        name = agents.get(aid, {}).get("name", str(aid))
        # Shorten name
        name = name.split("|")[0].strip() if "|" in name else name
        data.append({"name": name, "sentiment": mean_sent, "delta_n": delta_n,
                     "followers": k, "n0": n0})

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.set_title("Post Sentiment vs. ΔNeuroticism\n(marker size = follower count, NGE Run)",
                 fontsize=11)

    for d in data:
        size = max(50, d["followers"] * 80)
        color = "#C44E52" if d["delta_n"] > 0 else "#4C72B0"
        ax.scatter(d["sentiment"], d["delta_n"], s=size, color=color, alpha=0.6,
                   edgecolors="white", lw=0.8, zorder=3)
        # Label notable agents
        short = d["name"].split()[0] if d["name"] else ""
        ax.annotate(short, xy=(d["sentiment"], d["delta_n"]),
                    xytext=(4, 3), textcoords="offset points", fontsize=7.5, alpha=0.85)

    ax.axhline(0, color="black", lw=0.8, ls="--", alpha=0.4)
    ax.axvline(0, color="black", lw=0.8, ls="--", alpha=0.4)
    ax.set_xlabel("Mean Post Sentiment (−1 = negative, +1 = positive)", fontsize=10)
    ax.set_ylabel("ΔNeuroticism (final − seed)", fontsize=10)

    rise_patch = mpatches.Patch(color="#C44E52", alpha=0.6, label="N increased")
    fall_patch = mpatches.Patch(color="#4C72B0", alpha=0.6, label="N decreased")
    ax.legend(handles=[rise_patch, fall_patch], fontsize=9, frameon=False)

    plt.tight_layout()
    path = os.path.join(OUT, "fig4_sentiment_neuroticism.pdf")
    plt.savefig(path, bbox_inches="tight")
    plt.savefig(path.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"Saved {path}")
    plt.close()


# ── Figure 5: Individual Spaghetti — E and N trajectories ─────────────────────
def fig5_spaghetti(agents, snaps):
    by_agent = defaultdict(list)
    for s in snaps:
        by_agent[s["agent_id"]].append(s)

    fig, (ax_e, ax_n) = plt.subplots(1, 2, figsize=(11, 4.5))
    fig.suptitle("Individual Agent Trajectories (NGE Run, N=17)", fontsize=12)

    highlight = {
        "Asuka": "#C44E52",
        "Shinji": "#4C72B0",
        "Gendo": "#8172B2",
        "Toji": "#CCB974",
        "Ritsuko": "#55A868",
    }

    for aid, slist in by_agent.items():
        slist = sorted(slist, key=lambda x: x["tick_number"])
        ticks = [s["tick_number"] for s in slist]
        e_vals = [s["extraversion"] for s in slist]
        n_vals = [s["neuroticism"] for s in slist]
        name = agents.get(aid, {}).get("name", "")
        first = name.split()[0] if name else ""

        color = highlight.get(first, "#aaaaaa")
        lw = 2.0 if first in highlight else 0.8
        alpha = 0.9 if first in highlight else 0.35
        zorder = 3 if first in highlight else 1

        ax_e.plot(ticks, e_vals, color=color, lw=lw, alpha=alpha, zorder=zorder)
        ax_n.plot(ticks, n_vals, color=color, lw=lw, alpha=alpha, zorder=zorder)

        if first in highlight:
            ax_e.annotate(first, xy=(ticks[-1], e_vals[-1]),
                          xytext=(3, 0), textcoords="offset points", fontsize=8, color=color)
            ax_n.annotate(first, xy=(ticks[-1], n_vals[-1]),
                          xytext=(3, 0), textcoords="offset points", fontsize=8, color=color)

    for ax, trait, aval, label in [
        (ax_e, "extraversion", ATTRACTOR["extraversion"], "Extraversion"),
        (ax_n, "neuroticism", ATTRACTOR["neuroticism"], "Neuroticism"),
    ]:
        ax.axhline(aval, color="black", lw=1, ls="--", alpha=0.4)
        ax.annotate(f"T*≈{aval}", xy=(max(ticks), aval), xytext=(2, 3),
                    textcoords="offset points", fontsize=8, alpha=0.6)
        ax.set_xlabel("Tick", fontsize=10)
        ax.set_ylabel("Score (0–100)", fontsize=10)
        ax.set_title(label, fontsize=11)
        ax.set_ylim(0, 105)

    plt.tight_layout()
    path = os.path.join(OUT, "fig5_spaghetti.pdf")
    plt.savefig(path, bbox_inches="tight")
    plt.savefig(path.replace(".pdf", ".png"), bbox_inches="tight")
    print(f"Saved {path}")
    plt.close()


if __name__ == "__main__":
    print("Loading NGE data...")
    agents, snaps, posts, follows = load_nge()
    print(f"  {len(agents)} agents, {len(snaps)} snapshots, {len(posts)} posts")

    print("Generating Figure 2: NGE convergence...")
    fig2_nge_convergence(agents, snaps)

    print("Generating Figure 3: Attractor pull...")
    fig3_attractor_pull(agents, snaps)

    print("Generating Figure 4: Sentiment × ΔN...")
    fig4_sentiment_neuroticism(agents, snaps, posts, follows)

    print("Generating Figure 5: Spaghetti trajectories...")
    fig5_spaghetti(agents, snaps)

    print("\nAll figures saved to ../figures/")
    print("Note: Figure 1 (H2 grounded vs ungrounded) requires prod data.")
