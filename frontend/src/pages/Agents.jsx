import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";
import { useRun } from "../RunContext";
import Avatar from "../components/Avatar";

const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};
const SHORT = { openness: "O", conscientiousness: "C", extraversion: "E", agreeableness: "A", neuroticism: "N" };


function AgentCard({ agent }) {
  const p = agent.personality;
  return (
    <Link to={`/social/agents/${agent.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={{ cursor: "pointer", height: "100%", boxSizing: "border-box" }}>
        {/* Header */}
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 10 }}>
          <Avatar name={agent.name} handle={agent.handle} avatar={agent.avatar} size={44} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontWeight: 700, fontSize: 14, color: "var(--text-h)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
              {agent.name}
            </div>
            <div className="muted" style={{ fontSize: 12 }}>@{agent.handle}</div>
          </div>
          {agent.snapshot_count > 0 && (
            <span className="muted" style={{ fontSize: 11, whiteSpace: "nowrap" }}>
              {agent.snapshot_count} ✦
            </span>
          )}
        </div>

        {/* Bio */}
        {agent.bio && (
          <p style={{ fontSize: 12, lineHeight: 1.5, margin: "0 0 12px", color: "var(--text-h)" }}>
            {agent.bio}
          </p>
        )}

        {/* Trait pills */}
        <div style={{ display: "flex", gap: 5, flexWrap: "wrap" }}>
          {Object.entries(TRAIT_COLORS).map(([trait, color]) => {
            const val = p[trait];
            if (val == null) return null;
            const score = Math.round(val);
            return (
              <div key={trait} style={{
                display: "flex", alignItems: "center", gap: 4,
                padding: "3px 8px", borderRadius: 20,
                background: color + "18", border: `1px solid ${color}33`,
              }}>
                <span style={{ fontSize: 10, fontWeight: 700, color, letterSpacing: "0.3px" }}>{SHORT[trait]}</span>
                <span style={{ fontSize: 11, color: "var(--text-h)", fontWeight: 600 }}>{score}</span>
              </div>
            );
          })}
        </div>
      </div>
    </Link>
  );
}

export default function Agents() {
  const { viewingRunId } = useRun();
  const [agents, setAgents]   = useState([]);
  const [sort, setSort]       = useState("name");
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    api.listAgents(viewingRunId)
      .then(setAgents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [viewingRunId]);

  const sorted = [...agents].sort((a, b) => {
    if (sort === "name") return a.name.localeCompare(b.name);
    return a.id - b.id;
  });

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20, flexWrap: "wrap", gap: 10 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Agents</h1>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className="muted" style={{ fontSize: 12 }}>Sort:</span>
          {[["name", "Name"], ["id", "Default"]].map(([val, label]) => (
            <button key={val} className={`btn${sort === val ? " primary" : ""}`} onClick={() => setSort(val)}>
              {label}
            </button>
          ))}
        </div>
      </div>

      {error && <p className="error">{error}</p>}
      {sorted.length === 0 && <p className="muted">No agents yet.</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 10 }}>
        {sorted.map((a) => <AgentCard key={a.id} agent={a} />)}
      </div>
    </div>
  );
}
