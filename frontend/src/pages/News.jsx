import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine,
  ScatterChart, Scatter, ZAxis, CartesianGrid,
} from "recharts";
import { api } from "../api";
import PostCard from "../components/PostCard";

const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};

const EMOTION_COLORS = {
  anxiety:    "#ef4444",
  anger:      "#dc2626",
  outrage:    "#b91c1c",
  fear:       "#f97316",
  sadness:    "#6366f1",
  disgust:    "#a855f7",
  hope:       "#22c55e",
  optimism:   "#10b981",
  excitement: "#f59e0b",
  curiosity:  "#3b82f6",
  pride:      "#8b5cf6",
  surprise:   "#06b6d4",
};

function SentimentBadge({ sentiment, emotion }) {
  if (sentiment == null) return <span className="muted" style={{ fontSize: 11 }}>analyzing…</span>;
  const color = sentiment > 0.2 ? "#22c55e" : sentiment < -0.2 ? "#ef4444" : "#f59e0b";
  const emoColor = EMOTION_COLORS[emotion] ?? "var(--text)";
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
      <div style={{
        width: 8, height: 8, borderRadius: "50%", background: color, flexShrink: 0,
      }} />
      <span style={{ fontSize: 11, fontWeight: 600, color }}>
        {sentiment > 0 ? "+" : ""}{sentiment.toFixed(2)}
      </span>
      {emotion && (
        <span style={{ fontSize: 11, color: emoColor, fontStyle: "italic" }}>{emotion}</span>
      )}
    </div>
  );
}

function HeadlineRow({ item, selected, onSelect }) {
  return (
    <div
      onClick={() => onSelect(selected ? null : item)}
      style={{
        padding: "10px 12px",
        borderRadius: 8,
        cursor: "pointer",
        background: selected ? "var(--accent-bg, #1e1b4b22)" : "transparent",
        border: `1px solid ${selected ? "var(--accent-border, #6366f1)" : "var(--border)"}`,
        marginBottom: 6,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <a
            href={item.url}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{ fontSize: 13, color: "var(--text-h)", lineHeight: 1.4 }}
          >
            {item.title}
          </a>
          <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>
            {item.source} · {item.category}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 4, flexShrink: 0 }}>
          <SentimentBadge sentiment={item.sentiment} emotion={item.emotion} />
          <span className="muted" style={{ fontSize: 11 }}>{item.engagement} posts</span>
        </div>
      </div>
    </div>
  );
}

function HeadlinePosts({ item }) {
  const [posts, setPosts] = useState(null);
  useEffect(() => {
    api.newsPosts(item.id).then(setPosts).catch(() => setPosts([]));
  }, [item.id]);

  if (!posts) return <p className="muted">Loading…</p>;
  if (posts.length === 0) return <p className="muted">No posts yet for this headline.</p>;
  return (
    <div>
      {posts.map((p) => <PostCard key={p.id} post={p} />)}
    </div>
  );
}

export default function News() {
  const [items,       setItems]       = useState([]);
  const [sentiment,   setSentiment]   = useState([]);
  const [correlation, setCorrelation] = useState([]);
  const [selected,    setSelected]    = useState(null);
  const [traitX,      setTraitX]      = useState("neuroticism");
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(null);

  useEffect(() => {
    Promise.all([
      api.listNews(),
      api.newsSentimentOverTime(),
      api.newsPersonalityCorrelation(),
    ])
      .then(([n, s, c]) => { setItems(n); setSentiment(s); setCorrelation(c); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const analyzed = items.filter((i) => i.analyzed);

  return (
    <div>
      <h1 className="page-title" style={{ marginBottom: 20 }}>News</h1>

      {/* ── Section 1: Sentiment over time ── */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", marginBottom: 4 }}>
          News sentiment over time
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
          Average sentiment of headlines injected per tick
        </div>
        {sentiment.length === 0 ? (
          <p className="muted">No analyzed headlines yet — analysis runs every 30s in the background.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={sentiment} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="tick_number" tick={{ fontSize: 11 }} />
              <YAxis domain={[-1, 1]} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => v.toFixed(3)} labelFormatter={(t) => `tick ${t}`} />
              <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="4 4" />
              <Line type="monotone" dataKey="avg_sentiment" stroke="#6366f1" strokeWidth={2} dot={{ r: 3 }} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Section 2: Personality correlation ── */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 4 }}>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)" }}>
            Personality × news sentiment
          </div>
          <div style={{ display: "flex", gap: 4 }}>
            {Object.entries(TRAIT_COLORS).map(([trait, color]) => (
              <button
                key={trait}
                onClick={() => setTraitX(trait)}
                style={{
                  padding: "2px 8px", borderRadius: 12, fontSize: 11, fontWeight: 700,
                  border: `1px solid ${traitX === trait ? color : "var(--border)"}`,
                  background: traitX === trait ? color + "22" : "transparent",
                  color: traitX === trait ? color : "var(--text)",
                  cursor: "pointer",
                }}
              >
                {trait.slice(0, 3).toUpperCase()}
              </button>
            ))}
          </div>
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
          Does a higher {traitX} score correlate with engaging more negative or positive news?
        </div>
        {correlation.length < 2 ? (
          <p className="muted">Need more data — keep the simulation running.</p>
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <ScatterChart margin={{ top: 10, right: 20, left: -10, bottom: 0 }}>
              <CartesianGrid stroke="var(--border)" strokeDasharray="4 4" />
              <XAxis
                type="number" dataKey={traitX} domain={[0, 100]}
                tick={{ fontSize: 11 }} name={traitX}
                label={{ value: traitX, position: "insideBottomRight", offset: -5, fontSize: 11 }}
              />
              <YAxis
                type="number" dataKey="avg_sentiment" domain={[-1, 1]}
                tick={{ fontSize: 11 }} name="avg sentiment"
              />
              <ZAxis range={[40, 40]} />
              <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="4 4" />
              <Tooltip
                cursor={{ strokeDasharray: "3 3" }}
                content={({ payload }) => {
                  if (!payload?.length) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="card" style={{ padding: "8px 12px", fontSize: 12 }}>
                      <div style={{ fontWeight: 600 }}>@{d.agent_handle}</div>
                      <div>{traitX}: {Math.round(d[traitX])}</div>
                      <div>avg sentiment: {d.avg_sentiment.toFixed(3)}</div>
                      <div className="muted">{d.engagement_count} headlines</div>
                    </div>
                  );
                }}
              />
              <Scatter
                data={correlation}
                fill={TRAIT_COLORS[traitX]}
                fillOpacity={0.8}
              />
            </ScatterChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* ── Section 3: Headline feed ── */}
      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr", gap: 16 }}>
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", marginBottom: 12 }}>
            Headlines · {items.length} tracked · {analyzed.length} analyzed
          </div>
          {items.length === 0 ? (
            <p className="muted">No headlines yet — start the simulation to begin injecting news.</p>
          ) : (
            items.map((item) => (
              <HeadlineRow
                key={item.id}
                item={item}
                selected={selected?.id === item.id}
                onSelect={setSelected}
              />
            ))
          )}
        </div>

        {selected && (
          <div>
            <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", marginBottom: 8 }}>
              Posts reacting to this headline
            </div>
            <div className="muted" style={{ fontSize: 12, marginBottom: 12, lineHeight: 1.4 }}>
              &ldquo;{selected.title}&rdquo;
            </div>
            <HeadlinePosts item={selected} />
          </div>
        )}
      </div>
    </div>
  );
}
