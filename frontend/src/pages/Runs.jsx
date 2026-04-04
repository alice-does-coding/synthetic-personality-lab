import { useState } from "react";
import { api } from "../api";
import { useRun } from "../RunContext";

const mono = { fontFamily: "var(--mono)" };

const FIELD = ({ label, value, color }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
    <span style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", opacity: 0.4 }}>
      {label}
    </span>
    <span style={{ ...mono, fontSize: 12, color: color || "var(--text-h)", fontWeight: 700 }}>
      {value ?? "—"}
    </span>
  </div>
);

const Input = ({ label, value, onChange, placeholder, type = "text" }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", opacity: 0.5 }}>
      {label}
    </label>
    <input
      type={type}
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      style={{
        ...mono, fontSize: 11,
        background: "var(--bg)", color: "var(--text-h)",
        border: "1px solid var(--border)",
        padding: "5px 8px", outline: "none", width: "100%", boxSizing: "border-box",
      }}
    />
  </div>
);

const Toggle = ({ label, value, onChange }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", opacity: 0.5 }}>
      {label}
    </label>
    <button
      onClick={() => onChange(!value)}
      style={{
        ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
        padding: "4px 12px", cursor: "pointer", width: "fit-content",
        border: `1px solid ${value ? "#2dd4bf" : "#ff3ea5"}`,
        background: "var(--bg)",
        color: value ? "#2dd4bf" : "#ff3ea5",
      }}
    >
      {value ? "enabled" : "disabled"}
    </button>
  </div>
);

const Textarea = ({ label, value, onChange, placeholder, rows = 3 }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", opacity: 0.5 }}>
      {label}
    </label>
    <textarea
      value={value}
      onChange={e => onChange(e.target.value)}
      placeholder={placeholder}
      rows={rows}
      style={{
        ...mono, fontSize: 11,
        background: "var(--bg)", color: "var(--text-h)",
        border: "1px solid var(--border)",
        padding: "5px 8px", outline: "none", resize: "vertical", width: "100%", boxSizing: "border-box",
      }}
    />
  </div>
);

const DEFAULTS = {
  name: "",
  description: "",
  model: "mistral-large-latest",
  news_enabled: true,
  post_framing: "a user on a social media platform",
  ipip_framing: "your recent inner and outer life",
  seed_distribution: "random",
  agent_count: 30,
  tick_limit: 1000,
  tick_duration_s: 30,
  notes: "",
};

function CreateRunForm({ onCreated, onCancel }) {
  const [form, setForm] = useState(DEFAULTS);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const set = (key) => (val) => setForm(f => ({ ...f, [key]: val }));

  const submit = async () => {
    if (!form.name.trim()) { setError("name is required"); return; }
    setSaving(true); setError(null);
    try {
      const run = await api.createRun({
        ...form,
        agent_count: parseInt(form.agent_count) || null,
        tick_limit: parseInt(form.tick_limit) || null,
        tick_duration_s: parseInt(form.tick_duration_s) || null,
      });
      onCreated(run);
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const section = (title) => (
    <div style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", opacity: 0.3, borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
      {title}
    </div>
  );

  return (
    <div style={{ border: "1px solid var(--text-h)", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ ...mono, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-h)" }}>
        New Run
      </div>

      {section("identity")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Input label="name *" value={form.name} onChange={set("name")} placeholder="no-news-control" />
        <Input label="model" value={form.model} onChange={set("model")} placeholder="mistral-large-latest" />
      </div>
      <Textarea label="description" value={form.description} onChange={set("description")} placeholder="What is this run testing?" rows={2} />

      {section("stimulus")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Toggle label="news" value={form.news_enabled} onChange={set("news_enabled")} />
      </div>

      {section("framing")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Input label="post system prompt framing" value={form.post_framing} onChange={set("post_framing")} placeholder="a user on a social media platform" />
        <Input label="ipip framing" value={form.ipip_framing} onChange={set("ipip_framing")} placeholder="your recent inner and outer life" />
      </div>

      {section("seed")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 16 }}>
        <Input label="seed distribution" value={form.seed_distribution} onChange={set("seed_distribution")} placeholder="random" />
        <Input label="agent count" value={form.agent_count} onChange={set("agent_count")} type="number" />
      </div>

      {section("schedule")}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Input label="tick limit" value={form.tick_limit} onChange={set("tick_limit")} type="number" placeholder="1000" />
        <Input label="tick duration (seconds)" value={form.tick_duration_s} onChange={set("tick_duration_s")} type="number" placeholder="30" />
      </div>

      {section("notes")}
      <Textarea label="notes" value={form.notes} onChange={set("notes")} placeholder="Hypothesis, context, what changed..." rows={3} />

      {error && (
        <span style={{ ...mono, fontSize: 10, color: "#ff3ea5" }}>{error}</span>
      )}

      <div style={{ display: "flex", gap: 10 }}>
        <button
          onClick={submit}
          disabled={saving}
          style={{
            ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
            padding: "5px 20px", cursor: saving ? "default" : "pointer",
            border: "1px solid var(--text-h)",
            background: "var(--text-h)", color: "var(--bg)",
            opacity: saving ? 0.5 : 1,
          }}
        >
          {saving ? "creating..." : "create run"}
        </button>
        <button
          onClick={onCancel}
          style={{
            ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
            padding: "5px 20px", cursor: "pointer",
            border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)",
          }}
        >
          cancel
        </button>
      </div>
    </div>
  );
}

function RunCard({ run, isActive, isRunning, onActivate, onSeed, onStart, onStop }) {
  const progress = run.tick_limit ? Math.min(100, Math.round((run.tick_count ?? 0) / run.tick_limit * 100)) : null;

  return (
    <div style={{ border: `1px solid ${isActive ? "#2dd4bf" : "var(--border)"}`, padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
            <span style={{ ...mono, fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{run.name}</span>
            {isActive && <span style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "1px 7px", border: "1px solid #2dd4bf", color: "#2dd4bf" }}>active</span>}
          </div>
          {run.description && (
            <span style={{ ...mono, fontSize: 11, color: "var(--text)", opacity: 0.55, lineHeight: 1.5 }}>{run.description}</span>
          )}
        </div>
        <span style={{ ...mono, fontSize: 10, color: "var(--text)", opacity: 0.3, flexShrink: 0 }}>#{run.id}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 14 }}>
        <FIELD label="model" value={run.model} />
        <FIELD label="news" value={run.news_enabled ? "enabled" : "disabled"} color={run.news_enabled ? "#2dd4bf" : "#ff3ea5"} />
        <FIELD label="framing" value={run.post_framing} />
        <FIELD label="seed" value={run.seed_distribution} />
        <FIELD label="agents" value={run.agent_count} />
        <FIELD label="ticks" value={run.tick_limit ? `${run.tick_count ?? 0} / ${run.tick_limit}` : (run.tick_count ?? "—")} />
        <FIELD label="started" value={run.started_at ? run.started_at.slice(0, 10) : null} />
        <FIELD label="ended" value={run.ended_at ? run.ended_at.slice(0, 10) : "ongoing"} color={!run.ended_at ? "#2dd4bf" : null} />
      </div>

      {progress !== null && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ height: 2, background: "var(--border)" }}>
            <div style={{ height: 2, width: `${progress}%`, background: isActive ? "#2dd4bf" : "var(--text-h)" }} />
          </div>
          <span style={{ ...mono, fontSize: 9, color: "var(--text)", opacity: 0.35 }}>{progress}% complete</span>
        </div>
      )}

      {run.notes && (
        <div style={{ ...mono, borderTop: "1px solid var(--border)", paddingTop: 12, fontSize: 11, color: "var(--text)", opacity: 0.45, lineHeight: 1.6 }}>
          {run.notes}
        </div>
      )}

      {!isActive && (
        <div style={{ display: "flex", gap: 8 }}>
          <button
            onClick={() => onActivate(run.id)}
            style={{
              ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
              padding: "3px 14px", cursor: "pointer",
              border: "1px solid #2dd4bf", background: "var(--bg)", color: "#2dd4bf",
            }}
          >
            activate
          </button>
        </div>
      )}
    </div>
  );
}

export default function Runs() {
  const { runs, activeRunId, refresh } = useRun();
  const [activating, setActivating] = useState(null);
  const [creating, setCreating] = useState(false);

  const handleActivate = async (runId) => {
    setActivating(runId);
    try {
      await api.activateRun(runId);
      await refresh();
    } catch (e) {
      alert(`Failed to activate run: ${e.message}`);
    } finally {
      setActivating(null);
    }
  };

const handleCreated = async () => {
    setCreating(false);
    await refresh();
  };

  return (
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ ...mono, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", margin: 0 }}>
          Runs
        </h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ ...mono, fontSize: 10, color: "var(--text)", opacity: 0.4 }}>
            {runs.length} run{runs.length !== 1 ? "s" : ""}
          </span>
          {!creating && (
            <button
              onClick={() => setCreating(true)}
              style={{
                ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
                padding: "4px 14px", cursor: "pointer",
                border: "1px solid var(--text-h)", background: "var(--bg)", color: "var(--text-h)",
              }}
            >
              + new run
            </button>
          )}
        </div>
      </div>

      {creating && (
        <CreateRunForm
          onCreated={handleCreated}
          onCancel={() => setCreating(false)}
        />
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
        {runs.map(run => (
          <RunCard
            key={run.id}
            run={run}
            isActive={run.id === activeRunId}
            onActivate={handleActivate}
          />
        ))}
      </div>
    </div>
  );
}
