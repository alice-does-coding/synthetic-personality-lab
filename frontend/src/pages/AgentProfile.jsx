import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";
import { api } from "../api";
import PostCard from "../components/PostCard";
import MarkdownText from "../components/MarkdownText";

const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};

export default function AgentProfile() {
  const { id } = useParams();
  const [agent,      setAgent]     = useState(null);
  const [posts,      setPosts]     = useState([]);
  const [history,    setHistory]   = useState([]);
  const [monologue,  setMonologue] = useState([]);
  const [tab,          setTab]         = useState("posts");
  const [selectedTick, setSelectedTick] = useState(null);
  const [error,        setError]        = useState(null);
  const [loading,      setLoading]      = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAgent(id),
      api.listPosts(100, id),
      api.personalityHistory(id),
      api.monologue(id),
    ])
      .then(([a, p, h, m]) => { setAgent(a); setPosts(p); setHistory(h); setMonologue(m); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;
  if (!agent)  return null;

  const p = agent.personality;
  const topPosts = posts.filter((post) => post.parent_id === null);
  const comments = posts.filter((post) => post.parent_id !== null);

  return (
    <div>
      <Link to="/social/agents" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
        ← Agents
      </Link>

      {/* Agent header */}
      <div className="card" style={{ marginTop: 12, marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 className="page-title" style={{ margin: "0 0 2px" }}>{agent.name}</h1>
            <span className="muted">@{agent.handle}</span>
          </div>
          <span className="tag">agent</span>
        </div>
        {agent.bio && (
          <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.5, color: "var(--text-h)" }}>{agent.bio}</p>
        )}
        {p.openness != null && (
          <div style={{ marginTop: 14, display: "flex", gap: 16, flexWrap: "wrap" }}>
            {Object.entries(TRAIT_COLORS).map(([trait, color]) => (
              <div key={trait} style={{ textAlign: "center" }}>
                <div style={{ fontSize: 20, fontWeight: 700, color }}>
                  {Math.round(p[trait])}
                </div>
                <div style={{ fontSize: 10, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.5px" }}>
                  {trait.slice(0, 3)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: "flex", gap: 4, marginBottom: 16 }}>
        <button className={`btn${tab === "posts" ? " primary" : ""}`} onClick={() => setTab("posts")}>
          Posts ({topPosts.length})
        </button>
        <button className={`btn${tab === "comments" ? " primary" : ""}`} onClick={() => setTab("comments")}>
          Comments ({comments.length})
        </button>
        <button className={`btn${tab === "monologue" ? " primary" : ""}`} onClick={() => setTab("monologue")}>
          Monologue ({monologue.length})
        </button>
        <button className={`btn${tab === "personality" ? " primary" : ""}`} onClick={() => setTab("personality")}>
          Personality drift ({history.length})
        </button>
      </div>

      {/* Posts tab — top-level posts only */}
      {tab === "posts" && (
        topPosts.length === 0
          ? <p className="muted">No posts yet.</p>
          : topPosts.map((post) => <PostCard key={post.id} post={post} />)
      )}

      {/* Comments tab — replies with parent post context */}
      {tab === "comments" && (
        comments.length === 0 ? (
          <p className="muted">No comments yet.</p>
        ) : (
          comments.map((c) => (
            <div key={c.id} style={{ marginBottom: 12 }}>
              {c.parent_handle && (
                <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.7, marginBottom: 4, paddingLeft: 2 }}>
                  ↩ replying to <strong>@{c.parent_handle}</strong>
                  {c.parent_content && (
                    <span>: &ldquo;{c.parent_content.length > 80 ? c.parent_content.slice(0, 80) + "…" : c.parent_content}&rdquo;</span>
                  )}
                </div>
              )}
              <PostCard post={c} />
            </div>
          ))
        )
      )}

      {/* Monologue tab — thoughts the agent kept private */}
      {tab === "monologue" && (
        monologue.length === 0 ? (
          <p className="muted">No inner monologue yet.</p>
        ) : (
          monologue.map((t) => (
            <div key={t.id} className="card" style={{ marginBottom: 8 }}>
              <MarkdownText style={{ fontSize: 13, lineHeight: 1.6, color: "var(--text-h)" }}>{t.content}</MarkdownText>
              <div className="muted" style={{ fontSize: 11, marginTop: 6 }}>
                tick {t.tick_number} · {t.engagement_type ?? "organic"}
              </div>
            </div>
          ))
        )
      )}

      {/* Personality drift tab */}
      {tab === "personality" && (
        history.length === 0 ? (
          <p className="muted">No assessments yet.</p>
        ) : (
          <>
            <div className="card" style={{ marginBottom: 16 }}>
              <p className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                Click any point to see what {agent.name} was posting during that window.
              </p>
              <ResponsiveContainer width="100%" height={300}>
                <LineChart
                  data={history}
                  margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
                >
                  <XAxis dataKey="tick_number" label={{ value: "tick", position: "insideBottomRight", offset: -5, fontSize: 11 }} tick={{ fontSize: 11 }} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v) => v.toFixed(1)} />
                  <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
                  {Object.entries(TRAIT_COLORS).map(([trait, color]) => (
                    <Line
                      key={trait}
                      type="monotone"
                      dataKey={trait}
                      stroke={color}
                      strokeWidth={2}
                      dot={{ r: 4 }}
                      activeDot={{
                        r: 7,
                        cursor: "pointer",
                        onClick: (_, payload) => {
                          const tick = payload.payload.tick_number;
                          setSelectedTick((prev) => prev === tick ? null : tick);
                        },
                      }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>

            {selectedTick != null && (() => {
              const idx = history.findIndex((h) => h.tick_number === selectedTick);
              const prevTick = idx > 0 ? history[idx - 1].tick_number : 0;
              const snapshot = history[idx];
              const windowPosts = posts.filter(
                (p) => p.tick_number > prevTick && p.tick_number <= selectedTick
              );
              const radarData = Object.entries(TRAIT_COLORS).map(([trait, color]) => ({
                trait: trait.slice(0, 3).toUpperCase(),
                value: Math.round(snapshot[trait]),
                color,
              }));
              return (
                <div style={{ display: "flex", gap: 16, alignItems: "flex-start", flexWrap: "wrap" }}>
                  {/* Left: radar + bars */}
                  <div className="card" style={{ flexShrink: 0, width: 260 }}>
                    <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>tick {prevTick + 1}–{selectedTick}</div>
                    <RadarChart width={220} height={200} data={radarData}>
                      <PolarGrid stroke="var(--border)" />
                      <PolarAngleAxis
                        dataKey="trait"
                        tick={({ x, y, payload }) => {
                          const color = TRAIT_COLORS[Object.keys(TRAIT_COLORS).find(k => k.slice(0,3).toUpperCase() === payload.value)];
                          return (
                            <text x={x} y={y} fill={color} textAnchor="middle" dominantBaseline="central" fontSize={11} fontWeight={700}>
                              {payload.value}
                            </text>
                          );
                        }}
                      />
                      <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
                      <Radar dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.15} strokeWidth={2} />
                    </RadarChart>
                    <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                      {radarData.map(({ trait, value, color }) => (
                        <div key={trait} style={{ display: "flex", alignItems: "center", gap: 8 }}>
                          <span style={{ fontSize: 11, fontWeight: 700, color, width: 28 }}>{trait}</span>
                          <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2 }}>
                            <div style={{ width: `${value}%`, height: "100%", background: color, borderRadius: 2 }} />
                          </div>
                          <span style={{ fontSize: 11, width: 24, textAlign: "right" }}>{value}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Right: posts panel */}
                  <div style={{ flex: 1, maxHeight: 420, overflowY: "auto", display: "flex", flexDirection: "column", gap: 8 }}>
                    {windowPosts.length === 0
                      ? <p className="muted">No posts in this window.</p>
                      : windowPosts.map((post) => <PostCard key={post.id} post={post} />)
                    }
                  </div>
                </div>
              );
            })()}
          </>
        )
      )}
    </div>
  );
}
