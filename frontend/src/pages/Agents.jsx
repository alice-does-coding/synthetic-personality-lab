import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";

const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];
const SHORT   = { openness: "O", conscientiousness: "C", extraversion: "E", agreeableness: "A", neuroticism: "N" };

function TraitBar({ value }) {
  if (value == null) return <span className="muted" style={{ fontSize: 12 }}>—</span>;
  const pct = Math.round(value);
  const color = pct >= 70 ? "#22c55e" : pct >= 40 ? "#f59e0b" : "#ef4444";
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
      <div style={{ flex: 1, height: 4, background: "var(--border)", borderRadius: 2 }}>
        <div style={{ width: `${pct}%`, height: "100%", background: color, borderRadius: 2 }} />
      </div>
      <span style={{ fontSize: 11, width: 26, textAlign: "right" }}>{pct}</span>
    </div>
  );
}

function AgentCard({ agent }) {
  const p = agent.personality;
  return (
    <Link to={`/agents/${agent.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={{ marginBottom: 10, cursor: "pointer" }}>
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 10 }}>
          <div>
            <span style={{ fontWeight: 600, fontSize: 15, color: "var(--text-h)" }}>{agent.name}</span>
            <span className="muted" style={{ marginLeft: 6 }}>@{agent.handle}</span>
          </div>
          <span className="tag">agent</span>
        </div>
        {agent.bio && <p className="muted" style={{ marginBottom: 10, fontSize: 13 }}>{agent.bio}</p>}
        <div style={{ display: "grid", gap: 4 }}>
          {TRAITS.map((t) => (
            <div key={t} style={{ display: "grid", gridTemplateColumns: "14px 1fr", gap: 8, alignItems: "center" }}>
              <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text)" }}>{SHORT[t]}</span>
              <TraitBar value={p[t]} />
            </div>
          ))}
        </div>
      </div>
    </Link>
  );
}

export default function Agents() {
  const [agents, setAgents]   = useState([]);
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

  if (loading) return <p className="muted">Loading…</p>;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Agents</h1>
        <button className="btn primary" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cancel" : "+ New Agent"}
        </button>
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
      {agents.length === 0 && <p className="muted">No agents yet.</p>}
      {agents.map((a) => <AgentCard key={a.id} agent={a} />)}
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
