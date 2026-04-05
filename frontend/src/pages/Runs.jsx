import { useState, useEffect, useRef } from "react";
import { api } from "../api";
import { useRun } from "../RunContext";

const mono = { fontFamily: "var(--mono)" };

const DELETE_MESSAGES = {
  seeding:   { warning: "This run is currently seeding agents in the background.", action: "Cancel & Delete" },
  pending:   { warning: "This run is queued and has not started seeding yet.",     action: "Delete" },
  ready:     { warning: "This run is seeded and waiting in the queue.",             action: "Delete" },
  completed: { warning: "This run has completed.",                                  action: "Delete" },
  stopped:   { warning: "This run was manually stopped.",                           action: "Delete" },
};

function DeleteDialog({ run, onConfirm, onCancel }) {
  const msg = DELETE_MESSAGES[run.status] ?? DELETE_MESSAGES.stopped;
  return (
    <div style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.6)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div style={{
        ...mono,
        background: "var(--bg)", border: "1px solid var(--text-h)",
        padding: 28, maxWidth: 420, width: "100%", display: "flex", flexDirection: "column", gap: 20,
      }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-h)" }}>
          Delete run
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{run.name}</div>
          <div style={{ fontSize: 10, color: "#fb7185" }}>{msg.warning}</div>
          <div style={{ fontSize: 10, color: "var(--text-dim)" }}>
            All agents, posts, snapshots, and news data for this run will be permanently deleted.
          </div>
        </div>

        <div style={{ display: "flex", gap: 10 }}>
          <button
            onClick={onConfirm}
            style={{
              ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
              padding: "5px 18px", cursor: "pointer",
              border: "1px solid #fb7185", background: "#fb7185", color: "#000",
            }}
          >
            {msg.action}
          </button>
          <button
            onClick={onCancel}
            style={{
              ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em",
              padding: "5px 18px", cursor: "pointer",
              border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)",
            }}
          >
            cancel
          </button>
        </div>
      </div>
    </div>
  );
}

const FIELD = ({ label, value, color }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
    <span style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
      {label}
    </span>
    <span style={{ ...mono, fontSize: 12, color: color || "var(--text-h)", fontWeight: 700 }}>
      {value ?? "—"}
    </span>
  </div>
);

const Input = ({ label, value, onChange, placeholder, type = "text" }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
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
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
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
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
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

function autoName(model, newsEnabled, persona) {
  const now = new Date();
  const mm  = String(now.getMonth() + 1).padStart(2, "0");
  const dd  = String(now.getDate()).padStart(2, "0");
  const hh  = String(now.getHours()).padStart(2, "0");
  const min = String(now.getMinutes()).padStart(2, "0");
  const shortModel = model.replace(/-latest$/, "");
  const news = newsEnabled ? "news" : "no-news";
  const p = persona ? `-${persona}` : "";
  return `${mm}${dd}-${hh}${min}-${shortModel}-${news}${p}`;
}

const DEFAULTS = {
  name: "",
  description: "",
  model: "mistral-large-latest",
  news_enabled: true,
  post_framing: "a user on a social media platform",
  ipip_framing: "your recent inner and outer life",
  seed_distribution: "random",
  agent_count: 10,
  tick_limit: 50,
  tick_duration_s: 30,
  notes: "",
};

function CreateRunForm({ onCreated, onCancel }) {
  const [form, setForm] = useState(() => ({ ...DEFAULTS, name: autoName(DEFAULTS.model, DEFAULTS.news_enabled) }));
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const nameEdited = useRef(false);

  const set = (key) => (val) => setForm(f => {
    const next = { ...f, [key]: val };
    // Keep name in sync with model/news unless user has manually changed it
    if ((key === "model" || key === "news_enabled") && !nameEdited.current) {
      next.name = autoName(next.model, next.news_enabled);
    }
    return next;
  });

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
    <div style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
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
        <Input label="name *" value={form.name} onChange={(v) => { nameEdited.current = true; set("name")(v); }} placeholder="no-news-control" />
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

const STATUS_STYLE = {
  seeding:   { color: "#f472b6",  label: "seeding…" },
  pending:   { color: "#f472b6",  label: "seeding…" },
  ready:     { color: "#fb923c",  label: "queued" },
  running:   { color: "#2dd4bf",  label: "running" },
  completed: { color: "var(--text-dim)", label: "completed" },
  stopped:   { color: "var(--text-dim)", label: "stopped" },
};

function RunCard({ run, isActive, isRunning, queuePos, onActivate, onStart, onStop, onDeleteRequest }) {
  const progress = run.tick_limit ? Math.min(100, Math.round((run.tick_count ?? 0) / run.tick_limit * 100)) : null;
  const st = STATUS_STYLE[run.status] ?? STATUS_STYLE.stopped;
  const borderColor = isActive ? "#2dd4bf" : "var(--border)";

  return (
    <div style={{ border: `1px solid ${borderColor}`, padding: 20, display: "flex", flexDirection: "column", gap: 16 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ ...mono, fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{run.name}</span>
            {isActive && (
              <span style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "1px 7px", border: "1px solid #2dd4bf", color: "#2dd4bf" }}>
                active
              </span>
            )}
            <span style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "1px 7px", border: `1px solid ${st.color}`, color: st.color }}>
              {st.label}
            </span>
            {queuePos !== null && (
              <span style={{ ...mono, fontSize: 9, color: "var(--text-dim)" }}>#{queuePos} in queue</span>
            )}
          </div>
          {run.description && (
            <span style={{ ...mono, fontSize: 11, color: "var(--text)", lineHeight: 1.5 }}>{run.description}</span>
          )}
        </div>
        <span style={{ ...mono, fontSize: 10, color: "var(--text-dim)", flexShrink: 0 }}>#{run.id}</span>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(130px, 1fr))", gap: 14 }}>
        <FIELD label="model" value={run.model} />
        <FIELD label="news" value={run.news_enabled ? "enabled" : "disabled"} color={run.news_enabled ? "#2dd4bf" : "#ff3ea5"} />
        <FIELD label="framing" value={run.post_framing} />
        <FIELD label="seed" value={run.seed_distribution} />
        <FIELD label="agents" value={run.agent_count} />
        <FIELD label="ticks" value={run.tick_limit ? `${run.tick_count ?? 0} / ${run.tick_limit}` : (run.tick_count ?? "—")} />
        <FIELD label="started" value={run.started_at ? run.started_at.slice(0, 10) : null} />
        <FIELD label="ended" value={run.ended_at ? run.ended_at.slice(0, 10) : (isActive && isRunning ? "ongoing" : null)} color={isActive && isRunning ? "#2dd4bf" : null} />
      </div>

      {progress !== null && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ height: 2, background: "var(--track)" }}>
            <div style={{ height: 2, width: `${progress}%`, background: isActive ? "#2dd4bf" : "var(--text-dim)" }} />
          </div>
          <span style={{ ...mono, fontSize: 9, color: "var(--text-dim)" }}>{progress}% complete</span>
        </div>
      )}

      {run.notes && (
        <div style={{ ...mono, borderTop: "1px solid var(--border)", paddingTop: 12, fontSize: 11, color: "var(--text)", lineHeight: 1.6 }}>
          {run.notes}
        </div>
      )}

      <div style={{ display: "flex", gap: 8, justifyContent: "space-between", alignItems: "center" }}>
        <div style={{ display: "flex", gap: 8 }}>
          {/* Active run: start or stop depending on whether sim is ticking */}
          {isActive && run.status !== "completed" && run.status !== "seeding" && run.status !== "pending" && (
            isRunning ? (
              <button onClick={() => onStop(run.id)} style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "3px 14px", cursor: "pointer", border: "1px solid #fb7185", background: "var(--bg)", color: "#fb7185" }}>
                stop
              </button>
            ) : (
              <button onClick={() => onStart(run.id)} style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "3px 14px", cursor: "pointer", border: "1px solid #2dd4bf", background: "var(--bg)", color: "#2dd4bf" }}>
                start
              </button>
            )
          )}
          {/* Inactive run: offer to activate (loads it as the active run) */}
          {!isActive && (run.status === "stopped" || run.status === "ready" || run.status === "completed") && (
            <button onClick={() => onActivate(run.id)} style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "3px 14px", cursor: "pointer", border: "1px solid #fb923c", background: "var(--bg)", color: "#fb923c" }}>
              {run.status === "ready" ? "jump queue" : "activate"}
            </button>
          )}
        </div>
        {!isRunning || !isActive ? (
          <button onClick={() => onDeleteRequest(run)} style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "3px 10px", cursor: "pointer", border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text-dim)" }}>
            delete
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default function Runs() {
  const { runs, activeRunId, isRunning, refresh } = useRun();
  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null); // run object | null

  // Queue position among ready/seeding/pending runs (ordered by id)
  const queued = runs.filter(r => r.status === "ready" || r.status === "pending" || r.status === "seeding");

  const handleActivate = async (runId) => {
    try {
      await api.activateRun(runId);
      await refresh();
    } catch (e) {
      alert(`Failed to activate run: ${e.message}`);
    }
  };

  const handleStart = async (runId) => {
    try {
      await api.startRun(runId);
      await refresh();
    } catch (e) {
      alert(`Failed to start run: ${e.message}`);
    }
  };

  const handleStop = async (runId) => {
    try {
      await api.stopRun(runId);
      await refresh();
    } catch (e) {
      alert(`Failed to stop run: ${e.message}`);
    }
  };

  const handleDelete = async () => {
    const run = confirmDelete;
    setConfirmDelete(null);
    try {
      await api.deleteRun(run.id);
      await refresh();
    } catch (e) {
      alert(`Failed to delete run: ${e.message}`);
    }
  };

  const handleCreated = async () => {
    setCreating(false);
    await refresh();
  };

  return (
    <>
    {confirmDelete && (
      <DeleteDialog
        run={confirmDelete}
        onConfirm={handleDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    )}
    <div style={{ maxWidth: 900, margin: "0 auto", padding: 24, display: "flex", flexDirection: "column", gap: 20 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <h2 style={{ ...mono, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text)", margin: 0 }}>
          Runs
        </h2>
        <div style={{ display: "flex", gap: 10, alignItems: "center" }}>
          <span style={{ ...mono, fontSize: 10, color: "var(--text-dim)" }}>
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
            isRunning={isRunning && run.id === activeRunId}
            queuePos={queued.includes(run) ? queued.indexOf(run) + 1 : null}
            onActivate={handleActivate}
            onStart={handleStart}
            onStop={handleStop}
            onDeleteRequest={setConfirmDelete}
          />
        ))}
      </div>
    </div>
    </>
  );
}
