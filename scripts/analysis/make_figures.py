"""
Paper figures — designed to be visually striking.
Run from backend/ directory.
"""
import sqlite3, os, math
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.patheffects as pe
import numpy as np

DB  = os.path.join(os.path.dirname(__file__), "instance", "lab.db")
OUT = os.path.join(os.path.dirname(__file__), "..", "figures")
os.makedirs(OUT, exist_ok=True)

TRAITS  = ["openness","conscientiousness","extraversion","agreeableness","neuroticism"]
LABELS  = ["Openness","Conscientiousness","Extraversion","Agreeableness","Neuroticism"]
PALETTE = ["#4361EE","#3A86FF","#FF006E","#8338EC","#FB5607"]
ATTRACTOR = dict(zip(TRAITS, [60, 60, 65, 58, 47]))

BG    = "#0f0f1a"
LIGHT = "#1e1e2e"
WHITE = "#f0f0f8"
GREY  = "#888899"

plt.rcParams.update({
    "font.family":       "sans-serif",
    "font.size":         11,
    "text.color":        WHITE,
    "axes.facecolor":    LIGHT,
    "axes.edgecolor":    GREY,
    "axes.labelcolor":   WHITE,
    "axes.titlecolor":   WHITE,
    "figure.facecolor":  BG,
    "xtick.color":       GREY,
    "ytick.color":       GREY,
    "grid.color":        "#2a2a3e",
    "grid.linewidth":    0.6,
    "axes.spines.top":   False,
    "axes.spines.right": False,
})

# ── Helpers ───────────────────────────────────────────────────────────────────
def save(fig, name):
    for ext in ("pdf", "png"):
        p = os.path.join(OUT, f"{name}.{ext}")
        fig.savefig(p, bbox_inches="tight", facecolor=BG)
        print(f"  saved {p}")
    plt.close(fig)

def outline(ax, txt, x, y, **kw):
    """Text with a dark halo so it's readable on any background."""
    t = ax.text(x, y, txt, **kw)
    t.set_path_effects([
        pe.withStroke(linewidth=3, foreground=BG)
    ])
    return t

def load(run_id=1):
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    c = con.cursor()
    agents = {r["id"]: dict(r) for r in
              c.execute("SELECT id,name FROM agents WHERE run_id=?", (run_id,))}
    snaps  = c.execute(
        "SELECT agent_id,tick_number,openness,conscientiousness,extraversion,"
        "agreeableness,neuroticism FROM personality_snapshots WHERE run_id=? "
        "ORDER BY tick_number", (run_id,)).fetchall()
    posts  = c.execute(
        "SELECT agent_id,sentiment FROM posts WHERE run_id=? AND sentiment IS NOT NULL",
        (run_id,)).fetchall()
    follows = c.execute(
        "SELECT followee_id, COUNT(*) n FROM follows "
        "JOIN agents a ON follows.follower_id=a.id WHERE a.run_id=? "
        "GROUP BY followee_id", (run_id,)).fetchall()
    con.close()
    return agents, snaps, posts, follows


# ══════════════════════════════════════════════════════════════════════════════
# FIG 2 — Convergence: spaghetti of ALL individual trajectories per trait
#          grey ghosts + colored mean on top — shows the pull viscerally
# ══════════════════════════════════════════════════════════════════════════════
def fig2(agents, snaps):
    print("Fig 2: convergence…")
    by_tick   = defaultdict(list)
    by_agent  = defaultdict(list)
    for s in snaps:
        by_tick[s["tick_number"]].append(s)
        by_agent[s["agent_id"]].append(s)
    ticks = sorted(by_tick.keys())

    fig, axes = plt.subplots(1, 5, figsize=(16, 4.5))
    fig.suptitle(
        "Regardless of Starting Point, Every Agent Converges on the Same Profile\n"
        "Grey = individual agents  ·  Colored = population mean  ·  Dashed = T* (attractor)",
        fontsize=11, fontweight="bold", color=WHITE, y=1.05)

    for ax, trait, label, color, aval in zip(axes, TRAITS, LABELS, PALETTE,
                                              [ATTRACTOR[t] for t in TRAITS]):
        # Individual ghost trajectories
        for aid, sl in by_agent.items():
            sl = sorted(sl, key=lambda x: x["tick_number"])
            ts = [s["tick_number"] for s in sl]
            vs = [s[trait] for s in sl if s[trait] is not None]
            ts = ts[:len(vs)]
            ax.plot(ts, vs, color="#445566", lw=0.9, alpha=0.4, zorder=1)

        # Population mean + SD band
        means, sds = [], []
        for t in ticks:
            vals = [s[trait] for s in by_tick[t] if s[trait] is not None]
            m = sum(vals)/len(vals)
            sd = math.sqrt(sum((v-m)**2 for v in vals)/len(vals))
            means.append(m); sds.append(sd)
        means = np.array(means); sds = np.array(sds)

        ax.fill_between(ticks, means-sds, means+sds, alpha=0.25, color=color, zorder=2)
        ax.plot(ticks, means, color=color, lw=3, zorder=3)

        # Attractor line — thick & labelled
        ax.axhline(aval, color=color, lw=1.5, ls="--", alpha=0.9, zorder=2)

        # Show spread collapsing: annotate SD at tick 0 vs final
        sd0, sdf = sds[0], sds[-1]
        ax.annotate(f"SD={sd0:.0f}", xy=(ticks[0], means[0]),
                    xytext=(ticks[0]+2, means[0]+sd0+6),
                    fontsize=7, color="#aaaacc", ha="left",
                    arrowprops=dict(arrowstyle="-", color="#555566", lw=0.6))
        ax.annotate(f"SD={sdf:.0f}", xy=(ticks[-1], means[-1]),
                    xytext=(ticks[-1]-8, means[-1]+sdf+8),
                    fontsize=7, color=color, ha="right",
                    arrowprops=dict(arrowstyle="-", color=color, lw=0.6, alpha=0.5))

        ax.set_title(label, fontsize=11, fontweight="bold", pad=8, color=color)
        ax.set_xlabel("Tick", fontsize=9)
        ax.set_ylim(0, 115)
        ax.set_xlim(ticks[0], ticks[-1])
        ax.yaxis.grid(True); ax.set_axisbelow(True)
        if ax is axes[0]:
            ax.set_ylabel("Score (0–100)", fontsize=9)
        else:
            ax.set_yticklabels([])

        # Big T* label
        outline(ax, f"T*={aval}", (ticks[0]+ticks[-1])/2, aval+4,
                fontsize=9, ha="center", color=color, fontweight="bold")

    fig.tight_layout()
    save(fig, "fig2_nge_convergence")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 3 — Attractor pull: seed → Δ scatter, one panel per trait
# ══════════════════════════════════════════════════════════════════════════════
def fig3(agents, snaps):
    print("Fig 3: attractor pull…")
    by_agent = defaultdict(dict)
    for s in snaps:
        by_agent[s["agent_id"]][s["tick_number"]] = s

    fig, axes = plt.subplots(1, 5, figsize=(16, 4))
    fig.suptitle("The Attractor Pull: Seed Value Predicts Direction of Drift\n"
                 "Above T* → drift down   ·   Below T* → drift up",
                 fontsize=12, fontweight="bold", color=WHITE, y=1.05)

    for ax, trait, label, color, aval in zip(axes, TRAITS, LABELS, PALETTE,
                                              [ATTRACTOR[t] for t in TRAITS]):
        seeds, deltas, names = [], [], []
        for aid, td in by_agent.items():
            if len(td) < 2: continue
            t0, tf = min(td), max(td)
            v0, vf = td[t0][trait], td[tf][trait]
            if v0 is None or vf is None: continue
            seeds.append(v0); deltas.append(vf - v0)
            n = agents.get(aid, {}).get("name", "")
            names.append(n.split()[0])

        seeds = np.array(seeds); deltas = np.array(deltas)

        # Color by direction: above T* = warm, below = cool
        point_colors = [PALETTE[2] if s > aval else PALETTE[0] for s in seeds]
        ax.scatter(seeds, deltas, c=point_colors, s=70, zorder=4,
                   edgecolors=BG, linewidths=0.8)

        ax.axhline(0,    color=WHITE, lw=0.8, alpha=0.3)
        ax.axvline(aval, color=color, lw=1.5, ls="--", alpha=0.8)

        # Trend line
        if len(seeds) > 2:
            z = np.polyfit(seeds, deltas, 1)
            xs = np.linspace(0, 100, 100)
            ax.plot(xs, np.poly1d(z)(xs), color=WHITE, lw=1.2, alpha=0.35, ls="-")

        ax.set_title(label, fontsize=10, fontweight="bold", pad=6, color=color)
        ax.set_xlabel("Seed value", fontsize=9)
        ax.set_xlim(0, 105)
        ax.yaxis.grid(True); ax.set_axisbelow(True)
        if ax is axes[0]:
            ax.set_ylabel("Δ Score (final − seed)", fontsize=9)
        else:
            ax.set_yticklabels([])

        outline(ax, f"T*={aval}", aval+1, ax.get_ylim()[1]*0.88 if ax.get_ylim()[1] else 40,
                fontsize=8, color=color, fontweight="bold", ha="left")

    above = mpatches.Patch(color=PALETTE[2], label="Seeded above T* (pulled down)")
    below = mpatches.Patch(color=PALETTE[0], label="Seeded below T* (pulled up)")
    fig.legend(handles=[above, below], loc="lower center", ncol=2,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.06),
               labelcolor=WHITE)
    fig.tight_layout()
    save(fig, "fig3_attractor_pull")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 4 — Sentiment × ΔN scatter — the Ritsuko finding
# ══════════════════════════════════════════════════════════════════════════════
def fig4(agents, snaps, posts, follows):
    print("Fig 4: sentiment × ΔN…")
    by_agent_snaps = defaultdict(list)
    for s in snaps: by_agent_snaps[s["agent_id"]].append(s)

    by_agent_posts = defaultdict(list)
    for p in posts:
        if p["sentiment"] is not None:
            by_agent_posts[p["agent_id"]].append(p["sentiment"])

    follower_count = {r["followee_id"]: r["n"] for r in follows}

    data = []
    for aid, sl in by_agent_snaps.items():
        sl = sorted(sl, key=lambda x: x["tick_number"])
        if len(sl) < 2: continue
        n0 = sl[0]["neuroticism"]; nf = sl[-1]["neuroticism"]
        if n0 is None or nf is None: continue
        sents = by_agent_posts.get(aid, [])
        if not sents: continue
        name = agents.get(aid, {}).get("name", "")
        first = name.split()[0]
        data.append({
            "name":      first,
            "sentiment": sum(sents)/len(sents),
            "delta_n":   nf - n0,
            "followers": follower_count.get(aid, 0),
            "n0":        n0,
        })

    fig, ax = plt.subplots(figsize=(8, 6))
    fig.patch.set_facecolor(BG)
    ax.set_facecolor(LIGHT)

    # Quadrant shading
    ax.axhspan(0, 80, xmin=0, xmax=1, alpha=0.04, color=PALETTE[2])
    ax.axhspan(-80, 0, xmin=0, xmax=1, alpha=0.04, color=PALETTE[0])

    for d in data:
        k = d["followers"]
        size = 60 + k * 90
        rising = d["delta_n"] > 0
        color  = PALETTE[2] if rising else PALETTE[0]
        ax.scatter(d["sentiment"], d["delta_n"], s=size, color=color,
                   alpha=0.85, edgecolors=BG, linewidths=1.2, zorder=4)

        # Annotate notable agents
        # Only label the extreme/isolated agents inline — rest via callout
        if d["name"] in {"Asuka", "Hikari"}:
            outline(ax, d["name"], d["sentiment"]+0.01, d["delta_n"]+2,
                    fontsize=8, color=WHITE, ha="left")

    ax.axhline(0, color=WHITE, lw=0.8, alpha=0.4, ls="--")
    ax.axvline(0, color=WHITE, lw=0.6, alpha=0.3, ls=":")

    # Ritsuko callout
    ritsuko = next((d for d in data if d["name"]=="Ritsuko"), None)
    if ritsuko:
        ax.annotate(
            "Ritsuko — 1 follower\nNeg. posts, N falls 22pts\n← social isolation effect",
            xy=(ritsuko["sentiment"], ritsuko["delta_n"]),
            xytext=(-0.1, -35),
            fontsize=8.5, color=PALETTE[0], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=PALETTE[0], lw=1.2),
        )

    # Toji callout
    toji = next((d for d in data if d["name"]=="Toji"), None)
    if toji:
        ax.annotate(
            "Toji — N=5 → 72\n\"the simulation broke him\"",
            xy=(toji["sentiment"], toji["delta_n"]),
            xytext=(-0.8, 58),
            fontsize=8.5, color=PALETTE[2], fontweight="bold",
            arrowprops=dict(arrowstyle="->", color=PALETTE[2], lw=1.2),
        )

    ax.set_xlabel("Mean Post Sentiment  (−1 negative · +1 positive)", fontsize=10)
    ax.set_ylabel("ΔNeuroticism  (final − seed)", fontsize=10)
    ax.set_title("Social Connectivity Mediates Neuroticism Contagion\n"
                 "Marker size = follower count", fontsize=11, fontweight="bold", pad=10)
    ax.yaxis.grid(True); ax.set_axisbelow(True)

    rise = mpatches.Patch(color=PALETTE[2], alpha=0.85, label="N increased")
    fall = mpatches.Patch(color=PALETTE[0], alpha=0.85, label="N decreased")
    ax.legend(handles=[rise, fall], fontsize=9, frameon=False,
              loc="upper right", labelcolor=WHITE)

    fig.tight_layout()
    save(fig, "fig4_sentiment_neuroticism")


# ══════════════════════════════════════════════════════════════════════════════
# FIG 5 — Spaghetti: E and N individual trajectories
# ══════════════════════════════════════════════════════════════════════════════
HIGHLIGHT = {
    "Asuka":   PALETTE[2],
    "Shinji":  PALETTE[0],
    "Gendo":   PALETTE[3],
    "Toji":    PALETTE[4],
    "Ritsuko": PALETTE[1],
}

def fig5(agents, snaps):
    print("Fig 5: spaghetti…")
    by_agent = defaultdict(list)
    for s in snaps:
        by_agent[s["agent_id"]].append(s)

    fig, (ax_e, ax_n) = plt.subplots(1, 2, figsize=(13, 5))
    fig.suptitle("Individual Personality Trajectories — NGE Run (N=17)",
                 fontsize=13, fontweight="bold", color=WHITE, y=1.02)

    # Key story callouts per panel
    CALLOUTS = {
        "extraversion": {
            "Asuka":  ("Asuka\nE 72→99→59\n(most volatile)", "right"),
            "Gendo":  ("Gendo\nE 15→80", "right"),
        },
        "neuroticism": {
            "Shinji":  ("Shinji\nN 23→64 ↑", "left"),
            "Toji":    ("Toji\nN 5→72 ↑", "left"),
            "Ritsuko": ("Ritsuko\n1 follower\nN 72→50 ↓", "right"),
        },
    }

    for ax, trait, aval, title in [
        (ax_e, "extraversion", ATTRACTOR["extraversion"], "Extraversion"),
        (ax_n, "neuroticism",  ATTRACTOR["neuroticism"],  "Neuroticism"),
    ]:
        all_ticks = []
        agent_data = {}
        for aid, sl in by_agent.items():
            sl = sorted(sl, key=lambda x: x["tick_number"])
            ts   = [s["tick_number"] for s in sl]
            vals = [s[trait] for s in sl]
            name = agents.get(aid, {}).get("name", "")
            first = name.split()[0]
            all_ticks = ts

            if first in HIGHLIGHT:
                c, lw, alpha, z = HIGHLIGHT[first], 2.8, 1.0, 4
            else:
                c, lw, alpha, z = "#445566", 0.8, 0.3, 1

            ax.plot(ts, vals, color=c, lw=lw, alpha=alpha, zorder=z)
            if first in HIGHLIGHT:
                agent_data[first] = (ts, vals)
                # End-of-line label
                outline(ax, first, ts[-1]+1, vals[-1],
                        fontsize=8, fontweight="bold", color=c,
                        ha="left", va="center")

        # Callout annotations
        callouts = CALLOUTS.get(trait, {})
        for name, (text, side) in callouts.items():
            if name not in agent_data: continue
            ts, vals = agent_data[name]
            # Find peak/trough for interesting annotation point
            if "↑" in text:
                idx = vals.index(max(vals))
            elif "↓" in text:
                idx = vals.index(min(vals))
            else:
                idx = len(vals)//3
            tx, ty = ts[idx], vals[idx]
            c = HIGHLIGHT[name]
            xoff = 12 if side == "right" else -12
            yoff = 14 if ty < 60 else -18
            ax.annotate(text,
                xy=(tx, ty),
                xytext=(tx + xoff, ty + yoff),
                fontsize=7.5, color=c, fontweight="bold",
                ha="left" if side == "right" else "right",
                arrowprops=dict(arrowstyle="->", color=c, lw=1, alpha=0.7),
            )

        # Attractor dashed line
        ax.axhline(aval, color=WHITE, lw=1.5, ls="--", alpha=0.35)
        outline(ax, f"T* = {aval}", all_ticks[len(all_ticks)//4], aval + 4,
                fontsize=9, color=WHITE, fontweight="bold", ha="center")

        ax.set_xlabel("Tick", fontsize=10)
        ax.set_ylabel("Score (0–100)", fontsize=10)
        ax.set_title(title, fontsize=13, fontweight="bold", color=WHITE, pad=10)
        ax.set_ylim(0, 115)
        ax.yaxis.grid(True); ax.set_axisbelow(True)

    legend_handles = [mpatches.Patch(color=c, label=n)
                      for n, c in HIGHLIGHT.items()]
    fig.legend(handles=legend_handles, loc="lower center", ncol=5,
               fontsize=9, frameon=False, bbox_to_anchor=(0.5, -0.05),
               labelcolor=WHITE)

    fig.tight_layout()
    save(fig, "fig5_spaghetti")


# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("Loading NGE data…")
    agents, snaps, posts, follows = load(run_id=1)
    print(f"  {len(agents)} agents, {len(snaps)} snapshots")

    fig2(agents, snaps)
    fig3(agents, snaps)
    fig4(agents, snaps, posts, follows)
    fig5(agents, snaps)
    print("\nDone.")
