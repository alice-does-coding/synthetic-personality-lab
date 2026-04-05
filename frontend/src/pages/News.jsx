import { useState, useEffect } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  ReferenceLine, CartesianGrid, Cell,
} from "recharts";
import { api } from "../api";
import { useRun } from "../RunContext";
import PostCard from "../components/PostCard";

const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];
const TRAIT_COLORS = {
  openness:          "#a78bfa",
  conscientiousness: "#818cf8",
  extraversion:      "#f472b6",
  agreeableness:     "#2dd4bf",
  neuroticism:       "#fb7185",
};

const EMOTION_COLORS = {
  joy:      "#f472b6",
  surprise: "#c77dff",
  neutral:  "#555",
  sadness:  "#818cf8",
  anger:    "#fb7185",
  disgust:  "#a78bfa",
  fear:     "#ff3ea5",
  anxiety:  "#fb7185",
  optimism: "#2dd4bf",
  curiosity:"#a78bfa",
};

function SentimentBar({ value }) {
  if (value == null) return <span className="muted">—</span>;
  const color = value > 0.1 ? "#2dd4bf" : value < -0.1 ? "#fb7185" : "#555";
  return (
    <span style={{ color, fontWeight: 700, fontSize: 12 }}>
      {value > 0 ? "+" : ""}{value.toFixed(2)}
    </span>
  );
}

function SectionHeader({ label, sub }) {
  return (
    <div style={{ marginBottom: 12, borderBottom: "1px solid var(--border)", paddingBottom: 8 }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-h)" }}>
        {label}
      </div>
      {sub && <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>{sub}</div>}
    </div>
  );
}

function TraitTabs({ active, onChange }) {
  return (
    <div style={{ display: "flex", gap: 0 }}>
      {TRAITS.map((t) => {
        const on = active === t;
        return (
          <button key={t} onClick={() => onChange(t)} style={{
            fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
            textTransform: "uppercase", letterSpacing: "0.06em",
            padding: "3px 10px",
            border: "1px solid var(--border)",
            borderRight: "none",
            background: on ? TRAIT_COLORS[t] : "var(--bg)",
            color: on ? "#000" : TRAIT_COLORS[t],
            cursor: "pointer",
          }}>
            {t.slice(0, 3)}
          </button>
        );
      })}
      <div style={{ width: 1, background: "var(--border)" }} />
    </div>
  );
}

function HeadlineRow({ item, selected, onSelect }) {
  return (
    <div
      onClick={() => onSelect(selected ? null : item)}
      style={{
        padding: "8px 10px",
        cursor: "pointer",
        borderBottom: "1px solid var(--border)",
        background: selected ? "var(--accent-bg)" : "transparent",
        borderLeft: selected ? "2px solid var(--pink)" : "2px solid transparent",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ flex: 1 }}>
          <a
            href={item.url} target="_blank" rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4, textDecoration: "none" }}
          >
            {item.title}
          </a>
          <div style={{ fontSize: 10, color: "var(--text)", marginTop: 2, textTransform: "uppercase", letterSpacing: "0.06em" }}>
            {item.source} · {item.category}
            {item.emotion && <span style={{ color: EMOTION_COLORS[item.emotion] ?? "var(--text)", marginLeft: 6 }}>{item.emotion}</span>}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 3, flexShrink: 0 }}>
          <SentimentBar value={item.sentiment} />
          <span className="muted" style={{ fontSize: 10 }}>{item.engagement} posts</span>
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
  if (!posts) return <p className="muted" style={{ padding: 12 }}>loading…</p>;
  if (!posts.length) return <p className="muted" style={{ padding: 12 }}>no posts for this headline yet.</p>;
  return posts.map((p) => <PostCard key={p.id} post={p} />);
}

function TraitMiniBar({ score, color }) {
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 2, width: 48 }}>
      <div style={{ height: 4, background: "var(--border)", position: "relative" }}>
        <div style={{
          position: "absolute", left: 0, top: 0,
          width: `${score ?? 0}%`, height: "100%",
          background: color, opacity: 0.75,
        }} />
      </div>
      <span style={{ fontSize: 9, color, fontWeight: 700, textAlign: "right" }}>
        {score != null ? Math.round(score) : "—"}
      </span>
    </div>
  );
}

function SentimentMiniBar({ value }) {
  const pct = Math.abs(value) * 50; // 0–50% of half-width
  const positive = value >= 0;
  const color = positive ? "#2dd4bf" : "#fb7185";
  return (
    <div style={{ position: "relative", width: 120, height: 12 }}>
      {/* center line */}
      <div style={{ position: "absolute", left: "50%", top: 0, width: 1, height: "100%", background: "var(--border)" }} />
      {/* bar */}
      <div style={{
        position: "absolute",
        top: 2, height: 8,
        background: color,
        opacity: 0.6 + 0.4 * Math.abs(value),
        left:  positive ? "50%" : `calc(50% - ${pct}%)`,
        width: `${pct}%`,
      }} />
    </div>
  );
}

function AgentProfileGrid({ data }) {
  if (!data.length) return <p className="muted">need more analyzed posts — check back soon.</p>;

  const sorted = [...data].sort((a, b) => a.avg_sentiment - b.avg_sentiment);
  const colStyle = { fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: "var(--text)", padding: "0 8px 6px" };

  return (
    <div style={{ overflowX: "auto" }}>
      <table style={{ width: "100%", borderCollapse: "collapse", fontFamily: "var(--mono)" }}>
        <thead>
          <tr style={{ borderBottom: "1px solid var(--border)" }}>
            <th style={{ ...colStyle, textAlign: "left", paddingLeft: 0, width: 120 }}>agent</th>
            {TRAITS.map(t => (
              <th key={t} style={{ ...colStyle, textAlign: "center", color: TRAIT_COLORS[t] }}>
                {t.slice(0, 3)}
              </th>
            ))}
            <th style={{ ...colStyle, textAlign: "center", width: 160 }}>
              <span style={{ color: "#fb7185" }}>neg</span>
              <span style={{ color: "var(--text)", margin: "0 4px" }}>·</span>
              <span style={{ color: "#2dd4bf" }}>pos</span>
            </th>
            <th style={{ ...colStyle, textAlign: "right", width: 60 }}>score</th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((d) => (
            <tr key={d.agent_id} style={{ borderBottom: "1px solid var(--border)" }}>
              <td style={{ padding: "8px 0", fontSize: 12, color: "var(--text-h)", fontWeight: 600 }}>
                @{d.agent_handle}
              </td>
              {TRAITS.map(t => (
                <td key={t} style={{ padding: "8px 8px", textAlign: "center" }}>
                  <TraitMiniBar score={d[t]} color={TRAIT_COLORS[t]} />
                </td>
              ))}
              <td style={{ padding: "8px 8px", textAlign: "center" }}>
                <SentimentMiniBar value={d.avg_sentiment} />
              </td>
              <td style={{ padding: "8px 0", textAlign: "right", fontSize: 11, fontWeight: 700,
                color: d.avg_sentiment >= 0 ? "#2dd4bf" : "#fb7185" }}>
                {d.avg_sentiment >= 0 ? "+" : ""}{d.avg_sentiment.toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function News() {
  const { viewingRunId } = useRun();
  const [items,        setItems]        = useState([]);
  const [newsOverTime, setNewsOverTime] = useState([]);
  const [postOverTime, setPostOverTime] = useState([]);
  const [contagion,    setContagion]    = useState([]);
  const [correlation,  setCorrelation]  = useState([]);
  const [selected,     setSelected]     = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [error,        setError]        = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      api.listNews(viewingRunId),
      api.newsSentimentOverTime(viewingRunId),
      api.postSentimentOverTime(viewingRunId),
      api.sentimentContagion(viewingRunId),
      api.postPersonalityCorrelation(viewingRunId),
    ])
      .then(([n, ns, ps, c, corr]) => {
        setItems(n);
        setNewsOverTime(ns);
        setPostOverTime(ps);
        setContagion(c);
        setCorrelation(corr);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [viewingRunId]);

  if (loading) return <p className="muted" style={{ padding: 20 }}>loading…</p>;
  if (error)   return <p className="error"  style={{ padding: 20 }}>{error}</p>;

  const analyzed = items.filter((i) => i.analyzed);

  // Merge contagion series for the dual-line chart
  const contagionMerged = contagion.filter(d => d.news_sentiment != null && d.post_sentiment != null);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0 }}>

      {/* ── Row 1: two time-series side by side ── */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", borderBottom: "1px solid var(--border)" }}>

        {/* Post sentiment over time */}
        <div style={{ padding: 16, borderRight: "1px solid var(--border)" }}>
          <SectionHeader
            label="Post sentiment · over time"
            sub="avg sentiment of agent posts per tick"
          />
          {postOverTime.length === 0 ? (
            <p className="muted">posts are being analyzed in the background — check back in a minute.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={postOverTime} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="tick_number" tick={{ fontSize: 10, fontFamily: "var(--mono)" }} />
                <YAxis domain={[-1, 1]} tick={{ fontSize: 10, fontFamily: "var(--mono)" }} />
                <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="avg_sentiment" stroke="#ff3ea5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* News vs post sentiment — contagion */}
        <div style={{ padding: 16 }}>
          <SectionHeader
            label="Emotional contagion"
            sub="news sentiment (purple) vs post sentiment (pink) per tick"
          />
          {contagionMerged.length === 0 ? (
            <p className="muted">need both analyzed news and posts — check back soon.</p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <LineChart data={contagionMerged} margin={{ top: 8, right: 10, left: -20, bottom: 0 }}>
                <XAxis dataKey="tick_number" tick={{ fontSize: 10, fontFamily: "var(--mono)" }} />
                <YAxis domain={[-1, 1]} tick={{ fontSize: 10, fontFamily: "var(--mono)" }} />
                <ReferenceLine y={0} stroke="var(--border)" strokeDasharray="4 4" />
                <Line type="monotone" dataKey="news_sentiment" stroke="#c77dff" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="post_sentiment" stroke="#ff3ea5" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* ── Row 2: personality × post sentiment ── */}
      <div style={{ padding: 16, borderBottom: "1px solid var(--border)" }}>
        <SectionHeader
          label="personality × post sentiment"
          sub="each agent's full OCEAN profile alongside their avg post sentiment · sorted negative → positive"
        />
        <AgentProfileGrid data={correlation} />
      </div>

      {/* ── Row 3: headlines ── */}
      <div style={{ display: "grid", gridTemplateColumns: selected ? "1fr 1fr" : "1fr" }}>
        <div style={{ borderRight: selected ? "1px solid var(--border)" : "none" }}>
          <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-h)" }}>
              Headlines
            </span>
            <span className="muted" style={{ fontSize: 11, marginLeft: 8 }}>
              {items.length} tracked · {analyzed.length} analyzed
            </span>
          </div>
          {items.length === 0 ? (
            <p className="muted" style={{ padding: 16 }}>no headlines yet — start the simulation.</p>
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
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
              <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-h)" }}>
                Reactions
              </div>
              <div className="muted" style={{ fontSize: 11, marginTop: 2, lineHeight: 1.4 }}>
                {selected.title}
              </div>
            </div>
            <HeadlinePosts item={selected} />
          </div>
        )}
      </div>
    </div>
  );
}
