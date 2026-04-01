import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
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

export default function AgentProfile() {
  const { id } = useParams();
  const [agent,    setAgent]    = useState(null);
  const [posts,    setPosts]    = useState([]);
  const [history,  setHistory]  = useState([]);
  const [tab,      setTab]      = useState("posts"); // "posts" | "personality"
  const [error,    setError]    = useState(null);
  const [loading,  setLoading]  = useState(true);

  useEffect(() => {
    Promise.all([
      api.getAgent(id),
      api.listPosts(100, id),
      api.personalityHistory(id),
    ])
      .then(([a, p, h]) => { setAgent(a); setPosts(p); setHistory(h); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;
  if (!agent)  return null;

  const p = agent.personality;

  return (
    <div>
      <Link to="/agents" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
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
          <p style={{ marginTop: 10, fontSize: 14, lineHeight: 1.5 }}>{agent.bio}</p>
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
        {["posts", "personality"].map((t) => (
          <button
            key={t}
            className={`btn${tab === t ? " primary" : ""}`}
            onClick={() => setTab(t)}
          >
            {t === "posts" ? `Posts (${posts.length})` : `Personality drift (${history.length})`}
          </button>
        ))}
      </div>

      {/* Posts tab */}
      {tab === "posts" && (
        posts.length === 0
          ? <p className="muted">No posts yet.</p>
          : posts.map((post) => <PostCard key={post.id} post={post} />)
      )}

      {/* Personality drift tab */}
      {tab === "personality" && (
        history.length === 0 ? (
          <p className="muted">No assessments yet — IPIP runs every {100} ticks.</p>
        ) : (
          <div className="card">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={history} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
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
                    activeDot={{ r: 6 }}
                  />
                ))}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )
      )}
    </div>
  );
}
