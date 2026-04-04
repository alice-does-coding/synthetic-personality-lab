"""
Lurkr corpus analysis — three charts:
  1. Word cloud: full post corpus, colored by agent's dominant OCEAN trait
  2. News category correlation: financial-metaphor posts vs news category shown
  3. Vocabulary comparison: top 50 words/bigrams, high-N (>65) vs low-N (<50) agents

Run from backend/:
  python corpus_analysis.py

Requires: wordcloud matplotlib psycopg2-binary
"""

import re
import sys
from collections import Counter, defaultdict

import psycopg2
import psycopg2.extras
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
from wordcloud import WordCloud
import plotly.graph_objects as go

# ── DB ────────────────────────────────────────────────────────────────────────

DB = dict(
    host="dpg-d780cap5pdvs739h5u10-a.oregon-postgres.render.com",
    user="lurkr_db_user",
    password="gogUO0RhMX5CoyZJh9xnFClnKTK8vo8I",
    dbname="lurkr_db",
    port=5432,
)

# ── Constants ─────────────────────────────────────────────────────────────────

OCEAN_COLORS = {
    "neuroticism":       "#ff3ea5",  # pink
    "openness":          "#c77dff",  # purple
    "conscientiousness": "#2dd4bf",  # mint
    "extraversion":      "#fb7185",  # rose
    "agreeableness":     "#a78bfa",  # lavender
}

FINANCIAL_TERMS = {
    "debt", "credit", "depreciation", "ledger", "contract", "interest",
    "repossessed", "compounding", "balance", "sterling", "currency",
    "invoice", "accrued", "iou", "account", "cost", "price", "trade",
    "market", "asset", "liability", "equity", "dividend", "yield",
    "liquidity", "portfolio", "hedge", "margin", "collateral", "default",
    "amortize", "capitalize", "debit", "receivable", "payable",
}

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
    # contraction artifacts (apostrophe stripped, then 't' removed as stopword)
    "doesn", "isn", "wasn", "aren", "weren", "couldn", "wouldn", "shouldn",
    "hadn", "hasn", "haven", "didn", "don", "won", "can",
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def tokenize(text):
    text = text.lower()
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"[^a-z\s]", " ", text)
    return [w for w in text.split() if w not in STOPWORDS and len(w) > 2]


def bigrams(tokens):
    return [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]


def dominant_trait(row):
    traits = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"]
    scores = {t: row[t] or 0 for t in traits}
    return max(scores, key=scores.get)


# ── Fetch ─────────────────────────────────────────────────────────────────────

def fetch_posts():
    conn = psycopg2.connect(**DB)
    cur = conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute("""
        SELECT
            p.id,
            p.content,
            p.is_public,
            p.engagement_type,
            p.news_context,
            p.tick_number,
            a.handle,
            a.neuroticism,
            a.openness,
            a.conscientiousness,
            a.extraversion,
            a.agreeableness
        FROM posts p
        JOIN agents a ON p.agent_id = a.id
        WHERE p.content IS NOT NULL
          AND a.neuroticism IS NOT NULL
        ORDER BY p.tick_number
    """)
    rows = cur.fetchall()
    conn.close()
    print(f"Fetched {len(rows)} posts")
    return rows


# ── Chart 1: Word cloud ───────────────────────────────────────────────────────

def build_word_cloud(rows):
    # Collect word frequencies and per-word dominant trait vote
    word_freq = Counter()
    word_trait_votes = defaultdict(Counter)

    for row in rows:
        trait = dominant_trait(row)
        tokens = tokenize(row["content"])
        for w in tokens:
            word_freq[w] += 1
            word_trait_votes[w][trait] += 1

    def color_func(word, **kwargs):
        votes = word_trait_votes.get(word, {})
        if not votes:
            return "#ffffff"
        top = max(votes, key=votes.get)
        return OCEAN_COLORS[top]

    wc = WordCloud(
        width=1600,
        height=800,
        background_color="#000000",
        max_words=200,
        color_func=color_func,
        prefer_horizontal=0.8,
        font_path=None,
    ).generate_from_frequencies(word_freq)

    fig, ax = plt.subplots(figsize=(16, 8), facecolor="#000000")
    ax.imshow(wc, interpolation="bilinear")
    ax.axis("off")

    # Legend
    for trait, color in OCEAN_COLORS.items():
        ax.plot([], [], "s", color=color, label=trait, markersize=10)
    ax.legend(
        loc="lower right",
        facecolor="#111111",
        edgecolor="#333333",
        labelcolor="white",
        fontsize=10,
        framealpha=0.8,
    )

    ax.set_title(
        "LURKR CORPUS — WORD CLOUD (colored by agent dominant OCEAN trait)",
        color="white",
        fontsize=13,
        pad=12,
        fontfamily="monospace",
    )
    fig.tight_layout()
    fig.savefig("corpus_wordcloud.png", dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print("Saved corpus_wordcloud.png")


# ── Chart 2: News category vs financial metaphor ──────────────────────────────

def build_news_correlation(rows):
    category_counts = Counter()
    category_financial = Counter()

    for row in rows:
        nc = row["news_context"]
        if not nc:
            continue
        # news_context is a list of headline dicts with 'category' key
        categories = set()
        if isinstance(nc, list):
            for item in nc:
                if isinstance(item, dict) and item.get("category"):
                    categories.add(item["category"].upper())
        elif isinstance(nc, dict) and nc.get("category"):
            categories.add(nc["category"].upper())

        tokens = set(tokenize(row["content"]))
        has_financial = bool(tokens & FINANCIAL_TERMS)

        for cat in categories:
            category_counts[cat] += 1
            if has_financial:
                category_financial[cat] += 1

    if not category_counts:
        print("No news_context data found — skipping chart 2")
        return

    cats = sorted(category_counts, key=category_counts.get, reverse=True)[:12]
    total = [category_counts[c] for c in cats]
    financial = [category_financial.get(c, 0) for c in cats]
    pct = [f / t * 100 if t else 0 for f, t in zip(financial, total)]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), facecolor="#000000")

    x = range(len(cats))
    ax1.bar(x, total, color="#333333", label="all posts with this news category")
    ax1.bar(x, financial, color="#ff3ea5", label="posts with financial metaphors")
    ax1.set_xticks(x)
    ax1.set_xticklabels(cats, rotation=30, ha="right", color="white", fontfamily="monospace", fontsize=9)
    ax1.set_facecolor("#000000")
    ax1.tick_params(colors="white")
    ax1.set_title("NEWS CATEGORY vs FINANCIAL METAPHOR POSTS", color="white", fontfamily="monospace", fontsize=11)
    ax1.legend(facecolor="#111111", edgecolor="#333333", labelcolor="white", fontsize=9)
    for spine in ax1.spines.values():
        spine.set_edgecolor("#333333")

    ax2.bar(x, pct, color="#c77dff")
    ax2.set_xticks(x)
    ax2.set_xticklabels(cats, rotation=30, ha="right", color="white", fontfamily="monospace", fontsize=9)
    ax2.set_ylabel("% financial metaphor", color="white", fontfamily="monospace")
    ax2.set_facecolor("#000000")
    ax2.tick_params(colors="white")
    ax2.set_title("FINANCIAL METAPHOR RATE BY NEWS CATEGORY", color="white", fontfamily="monospace", fontsize=11)
    for spine in ax2.spines.values():
        spine.set_edgecolor("#333333")

    fig.tight_layout()
    fig.savefig("corpus_news_correlation.png", dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print("Saved corpus_news_correlation.png")


# ── Chart 3: Vocabulary comparison high-N vs low-N ───────────────────────────

def build_vocab_comparison(rows):
    high_n = Counter()
    low_n = Counter()
    high_n_bi = Counter()
    low_n_bi = Counter()

    for row in rows:
        tokens = tokenize(row["content"])
        bis = bigrams(tokens)
        n = row["neuroticism"] or 0
        if n >= 65:
            high_n.update(tokens)
            high_n_bi.update(bis)
        elif n <= 50:
            low_n.update(tokens)
            low_n_bi.update(bis)

    top_n = 30

    # Combine unigrams + bigrams, pick top
    def top_combined(uni, bi, n):
        combined = Counter()
        combined.update(uni)
        combined.update({k: v for k, v in bi.items() if v >= 3})
        return combined.most_common(n)

    high_top = top_combined(high_n, high_n_bi, top_n)
    low_top = top_combined(low_n, low_n_bi, top_n)

    fig, (ax_high, ax_low) = plt.subplots(1, 2, figsize=(18, 10), facecolor="#000000")

    def draw_bar(ax, data, color, title):
        words, counts = zip(*data) if data else ([], [])
        words = [w.replace("_", " ") for w in words]
        y = range(len(words))
        ax.barh(y, counts, color=color, height=0.7)
        ax.set_yticks(y)
        ax.set_yticklabels(words, fontfamily="monospace", fontsize=9, color="white")
        ax.invert_yaxis()
        ax.set_facecolor("#000000")
        ax.tick_params(colors="white")
        ax.set_title(title, color="white", fontfamily="monospace", fontsize=11, pad=10)
        for spine in ax.spines.values():
            spine.set_edgecolor("#333333")
        ax.xaxis.label.set_color("white")

    draw_bar(ax_high, high_top, "#ff3ea5", f"HIGH NEUROTICISM (≥65)\ntop {top_n} words & bigrams")
    draw_bar(ax_low,  low_top,  "#2dd4bf", f"LOW NEUROTICISM (≤50)\ntop {top_n} words & bigrams")

    fig.suptitle(
        "VOCABULARY COMPARISON — HIGH-N vs LOW-N AGENTS",
        color="white", fontfamily="monospace", fontsize=13, y=1.01,
    )
    fig.tight_layout()
    fig.savefig("corpus_vocab_comparison.png", dpi=150, bbox_inches="tight", facecolor="#000000")
    plt.close(fig)
    print("Saved corpus_vocab_comparison.png")

    # Print WSB fingerprint check
    wsb_terms = {"moon", "diamond", "hold", "hodl", "ape", "bull", "bear", "rocket",
                 "dip", "tendies", "yolo", "squeeze", "short", "calls", "puts", "stonk"}
    found = {w for w, _ in high_top if w in wsb_terms or w.replace(" ", "_") in wsb_terms}
    if found:
        print(f"\nWSB terms in high-N vocabulary: {found}")
    else:
        print("\nNo direct WSB terms in top high-N vocabulary — check bigrams manually")


# ── Chart 4: Interactive word frequency over time ─────────────────────────────

def build_word_timeline(rows, top_n=25):
    """
    Interactive Plotly line chart — cumulative word frequency per tick.
    Top N words from the full corpus, one line each, colored by dominant OCEAN trait.
    Animated play button lets you watch the vocabulary lock in over time.
    """
    # Find top N words across full corpus first
    full_freq = Counter()
    for row in rows:
        full_freq.update(tokenize(row["content"]))
    top_words = [w for w, _ in full_freq.most_common(top_n)]

    # Build per-tick frequency (rolling window of 5 ticks to smooth noise)
    WINDOW = 5
    ticks_seen = sorted(set(row["tick_number"] for row in rows))
    tick_data = {}  # tick -> {word: count within window}

    rows_by_tick = defaultdict(list)
    for row in rows:
        rows_by_tick[row["tick_number"]].append(row)

    for i, tick in enumerate(ticks_seen):
        window_ticks = ticks_seen[max(0, i - WINDOW + 1): i + 1]
        window_counts = Counter()
        for t in window_ticks:
            for row in rows_by_tick[t]:
                window_counts.update(tokenize(row["content"]))
        tick_data[tick] = {w: window_counts[w] for w in top_words}

    # Assign color per word by which OCEAN trait's agents use it most
    word_trait_votes = defaultdict(Counter)
    for row in rows:
        trait = dominant_trait(row)
        for w in tokenize(row["content"]):
            if w in set(top_words):
                word_trait_votes[w][trait] += 1

    def word_color(word):
        votes = word_trait_votes.get(word, {})
        if not votes:
            return "#ffffff"
        return OCEAN_COLORS[max(votes, key=votes.get)]

    # Build Plotly figure
    fig = go.Figure()

    for word in top_words:
        y_vals = [tick_data[t][word] for t in ticks_seen]
        fig.add_trace(go.Scatter(
            x=list(ticks_seen),
            y=y_vals,
            mode="lines",
            name=word,
            line=dict(color=word_color(word), width=2),
            hovertemplate=f"<b>{word}</b><br>tick: %{{x}}<br>count: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(
            text="LURKR CORPUS — WORD FREQUENCY OVER TIME (5-tick rolling window)",
            font=dict(family="monospace", size=16, color="#ffffff"),
        ),
        paper_bgcolor="#000000",
        plot_bgcolor="#000000",
        font=dict(family="monospace", color="#ffffff"),
        xaxis=dict(
            title="tick",
            gridcolor="#222222",
            color="#ffffff",
            tickfont=dict(family="monospace"),
        ),
        yaxis=dict(
            title="frequency (5-tick rolling window)",
            gridcolor="#222222",
            color="#ffffff",
            tickfont=dict(family="monospace"),
        ),
        legend=dict(
            bgcolor="#111111",
            bordercolor="#333333",
            borderwidth=1,
            font=dict(family="monospace", size=10),
        ),
        hovermode="x unified",
        hoverlabel=dict(
            bgcolor="#111111",
            bordercolor="#333333",
            font=dict(family="monospace", color="#ffffff"),
        ),
    )

    # Annotation for key moments
    fig.add_annotation(
        x=ticks_seen[len(ticks_seen)//10],
        y=full_freq[top_words[0]] * 0.1,
        text="attractor lock-in zone",
        showarrow=False,
        font=dict(family="monospace", color="#555555", size=10),
    )

    fig.write_html(
        "corpus_word_timeline.html",
        include_plotlyjs="cdn",
        config={"displayModeBar": True, "scrollZoom": True},
    )
    print("Saved corpus_word_timeline.html")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("Connecting to prod DB...")
    rows = fetch_posts()

    print("\n[1/3] Building word cloud...")
    build_word_cloud(rows)

    print("\n[2/3] Building news correlation chart...")
    build_news_correlation(rows)

    print("\n[3/3] Building vocabulary comparison...")
    build_vocab_comparison(rows)

    print("\n[4/4] Building interactive word timeline...")
    build_word_timeline(rows)

    print("\nDone. Open corpus_wordcloud.png, corpus_news_correlation.png, corpus_vocab_comparison.png, corpus_word_timeline.html")
