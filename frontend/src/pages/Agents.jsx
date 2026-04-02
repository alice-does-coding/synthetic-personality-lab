import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};
const SHORT = { openness: "O", conscientiousness: "C", extraversion: "E", agreeableness: "A", neuroticism: "N" };

function Avatar({ name, dominantColor }) {
  const initials = name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  return (
    <div style={{
      width: 44, height: 44, borderRadius: "50%", flexShrink: 0,
      background: dominantColor + "22",
      border: `2px solid ${dominantColor}44`,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontSize: 15, fontWeight: 700, color: dominantColor,
    }}>
      {initials}
    </div>
  );
}

function AgentCard({ agent }) {
  const p = agent.personality;
  const dominant = Object.entries(TRAIT_COLORS).reduce((best, [trait]) =>
    (p[trait] ?? 0) > (p[best] ?? 0) ? trait : best
  , "openness");

  return (
    <Link to={`/agents/${agent.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={{ cursor: "pointer", height: "100%", boxSizing: "border-box" }}>
        {/* Header */}
        <div style={{ display: "flex", gap: 12, alignItems: "flex-start", marginBottom: 10 }}>
          <Avatar name={agent.name} dominantColor={TRAIT_COLORS[dominant]} />
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
          <p style={{ fontSize: 12, lineHeight: 1.5, margin: "0 0 12px", color: "var(--text)", opacity: 0.8 }}>
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
  const [agents, setAgents]   = useState([]);
  const [sort, setSort]       = useState("assessments");
  const [error, setError]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [form, setForm]       = useState({ name: "", handle: "", bio: "" });
  const [creating, setCreating] = useState(false);
  const [showForm, setShowForm] = useState(false);

  const load = () =>
    api.listAgents()
      .then(setAgents)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  const submit = async (e) => {
    e.preventDefault();
    setCreating(true);
    try {
      await api.createAgent(form);
      setForm({ name: "", handle: "", bio: "" });
      setShowForm(false);
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const sorted = [...agents].sort((a, b) => {
    if (sort === "assessments") return b.snapshot_count - a.snapshot_count;
    if (sort === "name")        return a.name.localeCompare(b.name);
    return a.id - b.id;
  });

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Agents</h1>
        <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
          <span className="muted" style={{ fontSize: 12 }}>Sort:</span>
          {[["assessments", "Most assessed"], ["name", "Name"], ["id", "Default"]].map(([val, label]) => (
            <button key={val} className={`btn${sort === val ? " primary" : ""}`} onClick={() => setSort(val)}>
              {label}
            </button>
          ))}
          <button className="btn primary" onClick={() => setShowForm((v) => !v)}>
            {showForm ? "Cancel" : "+ New Agent"}
          </button>
        </div>
      </div>

      {showForm && (
        <form onSubmit={submit} className="card" style={{ marginBottom: 20, display: "grid", gap: 10 }}>
          <input
            required placeholder="Name"
            value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
            style={inputStyle}
          />
          <input
            required placeholder="Handle (no spaces)"
            value={form.handle} onChange={(e) => setForm({ ...form, handle: e.target.value.toLowerCase().replace(/\s/g, "") })}
            style={inputStyle}
          />
          <input
            placeholder="Bio (optional)"
            value={form.bio} onChange={(e) => setForm({ ...form, bio: e.target.value })}
            style={inputStyle}
          />
          <button className="btn primary" disabled={creating} type="submit">
            {creating ? "Creating…" : "Create Agent"}
          </button>
        </form>
      )}

      {error && <p className="error">{error}</p>}
      {sorted.length === 0 && <p className="muted">No agents yet.</p>}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 10 }}>
        {sorted.map((a) => <AgentCard key={a.id} agent={a} />)}
      </div>
    </div>
  );
}

const inputStyle = {
  padding: "7px 10px",
  borderRadius: 6,
  border: "1px solid var(--border)",
  background: "var(--bg)",
  color: "var(--text-h)",
  fontSize: 14,
  width: "100%",
  boxSizing: "border-box",
};
