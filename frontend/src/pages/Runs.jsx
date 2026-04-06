import { useState, useRef, useEffect } from "react";
import { api } from "../api";
import { useRun } from "../RunContext";
import { useAdmin } from "../AdminContext";

const mono = { fontFamily: "var(--mono)" };

// ── Status ────────────────────────────────────────────────────────────────────
const STATUS_STYLE = {
  seeding:   { color: "#f472b6",        label: "seeding…" },
  pending:   { color: "#f472b6",        label: "seeding…" },
  ready:     { color: "#fb923c",        label: "queued"    },
  running:   { color: "#2dd4bf",        label: "running"   },
  completed: { color: "var(--text-dim)", label: "completed" },
  stopped:   { color: "var(--text-dim)", label: "stopped"   },
  failed:    { color: "#fb7185",        label: "failed"    },
};

// ── Small shared components ───────────────────────────────────────────────────
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

const Btn = ({ children, onClick, color = "var(--text)", border = "var(--border)", bg = "var(--bg)", disabled, style = {} }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em",
      padding: "3px 12px", cursor: disabled ? "default" : "pointer",
      border: `1px solid ${border}`, background: bg, color,
      opacity: disabled ? 0.4 : 1,
      ...style,
    }}
  >
    {children}
  </button>
);

// ── Delete confirmation dialog ────────────────────────────────────────────────
const DELETE_MESSAGES = {
  seeding:   { warning: "This run is currently seeding agents.",        action: "Cancel & Delete" },
  pending:   { warning: "This run is queued and has not started yet.",  action: "Delete" },
  ready:     { warning: "This run is seeded and waiting in the queue.", action: "Delete" },
  completed: { warning: "This run has completed.",                      action: "Delete" },
  stopped:   { warning: "This run was manually stopped.",               action: "Delete" },
  failed:    { warning: "This run failed due to a data quality error.", action: "Delete" },
};

function DeleteDialog({ run, onConfirm, onCancel }) {
  const msg = DELETE_MESSAGES[run.status] ?? DELETE_MESSAGES.stopped;
  return (
    <div onClick={onCancel} style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.6)", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div onClick={e => e.stopPropagation()} style={{ ...mono, background: "var(--bg)", border: "1px solid var(--text-h)", padding: 28, maxWidth: 400, width: "100%", display: "flex", flexDirection: "column", gap: 16 }}>
        <div style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-h)" }}>Delete run</div>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-h)" }}>{run.name}</div>
          <div style={{ fontSize: 10, color: "#fb7185" }}>{msg.warning}</div>
          <div style={{ fontSize: 10, color: "var(--text-dim)" }}>All agents, posts, snapshots, and news data will be permanently deleted.</div>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <Btn onClick={onConfirm} color="#000" border="#fb7185" bg="#fb7185">{msg.action}</Btn>
          <Btn onClick={onCancel}>cancel</Btn>
        </div>
      </div>
    </div>
  );
}

// ── Create run form (shown in a modal) ────────────────────────────────────────
const Input = ({ label, value, onChange, placeholder, type = "text" }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>{label}</label>
    <input type={type} value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder}
      style={{ ...mono, fontSize: 11, background: "var(--bg)", color: "var(--text-h)", border: "1px solid var(--border)", padding: "5px 8px", outline: "none", width: "100%", boxSizing: "border-box" }} />
  </div>
);

const Toggle = ({ label, value, onChange }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>{label}</label>
    <button onClick={() => onChange(!value)} style={{ ...mono, fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", padding: "4px 12px", cursor: "pointer", width: "fit-content", border: `1px solid ${value ? "#2dd4bf" : "#ff3ea5"}`, background: "var(--bg)", color: value ? "#2dd4bf" : "#ff3ea5" }}>
      {value ? "enabled" : "disabled"}
    </button>
  </div>
);

const Textarea = ({ label, value, onChange, placeholder, rows = 3 }) => (
  <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
    <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>{label}</label>
    <textarea value={value} onChange={e => onChange(e.target.value)} placeholder={placeholder} rows={rows}
      style={{ ...mono, fontSize: 11, background: "var(--bg)", color: "var(--text-h)", border: "1px solid var(--border)", padding: "5px 8px", outline: "none", resize: "vertical", width: "100%", boxSizing: "border-box" }} />
  </div>
);

const PROVIDERS = [
  { value: "mistral", label: "Mistral" },
  { value: "hf",      label: "HuggingFace" },
];

const PROVIDER_MODELS = {
  mistral: [
    { value: "mistral-large-latest", label: "mistral-large" },
    { value: "mistral-small-latest", label: "mistral-small" },
    { value: "open-mistral-nemo",    label: "mistral-nemo"  },
  ],
  hf: [
    { value: "Qwen/Qwen2.5-72B-Instruct",   label: "Qwen 2.5 72B"  },
    { value: "Qwen/Qwen2.5-7B-Instruct",    label: "Qwen 2.5 7B"   },
  ],
};

function shortModelLabel(model) {
  // HF model IDs: "meta-llama/Meta-Llama-3.1-70B-Instruct" → "llama31-70b"
  if (model.includes("/")) {
    return model.split("/")[1]
      .replace(/[-_]instruct$/i, "")
      .replace(/Meta-Llama-/i, "llama")
      .replace(/Qwen/i, "qwen")
      .replace(/[.-]/g, "")
      .toLowerCase()
      .slice(0, 12);
  }
  return model
    .replace(/-latest$/, "")
    .replace(/^open-/, "")
    .replace(/^mistral-/, "")
    .replace(/-/g, "");
}

function autoName(model, newsEnabled, persona, tickLimit) {
  const now = new Date();
  const mm  = String(now.getMonth() + 1).padStart(2, "0");
  const dd  = String(now.getDate()).padStart(2, "0");
  const hh  = String(now.getHours()).padStart(2, "0");
  const min = String(now.getMinutes()).padStart(2, "0");
  const ss  = String(now.getSeconds()).padStart(2, "0");
  const news = newsEnabled ? "news" : "no-news";
  const p = persona ? `-${persona}` : "";
  const t = tickLimit ? `-t${tickLimit}` : "";
  return `${mm}${dd}-${hh}${min}${ss}-${shortModelLabel(model)}-${news}${p}${t}`;
}

const DEFAULTS = {
  name: "", description: "", provider: "hf", model: "Qwen/Qwen2.5-72B-Instruct",
  news_enabled: true, batch_mode: true, ipip_grounded: true,
  random_seed: "", name_pool_text: "", agent_framing: "",
  persona: null, agent_count: 50, tick_limit: 100, notes: "",
};

function CreateRunModal({ onCreated, onClose }) {
  const [form, setForm] = useState(() => ({ ...DEFAULTS, name: autoName(DEFAULTS.model, DEFAULTS.news_enabled, null, DEFAULTS.tick_limit) }));
  const [personas, setPersonas] = useState([]);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);
  const nameEdited = useRef(false);

  useState(() => { api.listPersonas().then(setPersonas).catch(() => {}); });

  const set = (key) => (val) => setForm(f => {
    const next = { ...f, [key]: val };
    // When provider changes, reset model to first option for that provider
    if (key === "provider") {
      next.model = PROVIDER_MODELS[val]?.[0]?.value ?? next.model;
    }
    if (!nameEdited.current) {
      next.name = autoName(
        key === "model"        ? val : (key === "provider" ? next.model : next.model),
        key === "news_enabled" ? val : next.news_enabled,
        key === "persona"      ? val : next.persona,
        key === "tick_limit"   ? val : next.tick_limit,
      );
    }
    return next;
  });

  const submit = async () => {
    if (!form.name.trim()) { setError("name is required"); return; }
    setSaving(true); setError(null);
    try {
      await api.createRun({
        ...form,
        post_framing: form.agent_framing,
        agent_count:  parseInt(form.agent_count) || null,
        tick_limit:   parseInt(form.tick_limit)  || null,
        random_seed:  form.random_seed !== "" ? parseInt(form.random_seed) : null,
        name_pool:    form.name_pool_text.trim()
          ? form.name_pool_text.split("\n").map(s => s.trim()).filter(Boolean)
          : null,
      });
      onCreated();
    } catch (e) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const SectionLabel = ({ children }) => (
    <div style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", borderBottom: "1px solid var(--border)", paddingBottom: 6 }}>
      {children}
    </div>
  );

  const selectedPersona = personas.find(p => p.key === form.persona) ?? null;

  return (
    <div onClick={onClose} style={{ position: "fixed", inset: 0, zIndex: 1000, background: "rgba(0,0,0,0.7)", display: "flex", alignItems: "center", justifyContent: "center", padding: 24 }}>
      <div onClick={e => e.stopPropagation()} style={{ background: "var(--bg)", border: "1px solid var(--text-h)", padding: 28, width: "100%", maxWidth: 600, maxHeight: "90vh", overflowY: "auto", display: "flex", flexDirection: "column", gap: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <span style={{ ...mono, fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.08em", color: "var(--text-h)" }}>New Run</span>
          <button onClick={onClose} style={{ ...mono, fontSize: 16, background: "none", border: "none", color: "var(--text-dim)", cursor: "pointer", lineHeight: 1 }}>×</button>
        </div>

        <SectionLabel>identity</SectionLabel>
        <Input label="name *" value={form.name} onChange={v => { nameEdited.current = true; set("name")(v); }} placeholder="no-news-control" />
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>provider</label>
            <div style={{ display: "flex", gap: 2 }}>
              {PROVIDERS.map(p => (
                <button key={p.value} onClick={() => set("provider")(p.value)} style={{ ...mono, fontSize: 10, fontWeight: 700, padding: "4px 10px", cursor: "pointer", border: `1px solid ${form.provider === p.value ? "var(--text-h)" : "var(--border)"}`, background: form.provider === p.value ? "var(--text-h)" : "var(--bg)", color: form.provider === p.value ? "var(--bg)" : "var(--text)" }}>
                  {p.label}
                </button>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
            <label style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>model</label>
            <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
              {(PROVIDER_MODELS[form.provider] ?? []).map(m => (
                <button key={m.value} onClick={() => set("model")(m.value)} style={{ ...mono, fontSize: 10, fontWeight: 700, padding: "4px 10px", cursor: "pointer", border: `1px solid ${form.model === m.value ? "var(--text-h)" : "var(--border)"}`, background: form.model === m.value ? "var(--text-h)" : "var(--bg)", color: form.model === m.value ? "var(--bg)" : "var(--text)" }}>
                  {m.label}
                </button>
              ))}
            </div>
          </div>
        </div>
        <Textarea label="description" value={form.description} onChange={set("description")} placeholder="What is this run testing?" rows={2} />

        <SectionLabel>stimulus</SectionLabel>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <Toggle label="news" value={form.news_enabled} onChange={set("news_enabled")} />
          <Toggle label="batch mode" value={form.batch_mode} onChange={set("batch_mode")} />
        </div>

        <SectionLabel>population</SectionLabel>
        <div style={{ display: "flex", gap: 2, flexWrap: "wrap" }}>
          <button onClick={() => set("persona")(null)} style={{ ...mono, fontSize: 10, fontWeight: 700, padding: "4px 10px", cursor: "pointer", border: `1px solid ${form.persona === null ? "var(--text-h)" : "var(--border)"}`, background: form.persona === null ? "var(--text-h)" : "var(--bg)", color: form.persona === null ? "var(--bg)" : "var(--text)" }}>
            population norms
          </button>
          {personas.map(p => (
            <button key={p.key} onClick={() => set("persona")(p.key)} style={{ ...mono, fontSize: 10, fontWeight: 700, padding: "4px 10px", cursor: "pointer", border: `1px solid ${form.persona === p.key ? "var(--pink)" : "var(--border)"}`, background: form.persona === p.key ? "var(--pink)" : "var(--bg)", color: form.persona === p.key ? "#000" : "var(--text)" }}>
              {p.label}
            </button>
          ))}
        </div>
        {selectedPersona && <span style={{ ...mono, fontSize: 10, color: "var(--text)", opacity: 0.7 }}>{selectedPersona.description}</span>}
        <Textarea label="name pool (one per line)" value={form.name_pool_text} onChange={set("name_pool_text")} placeholder={"Dolly Parton\nDavid Bowie\n..."} rows={3} />

        <SectionLabel>framing & scale</SectionLabel>
        <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr 1fr", gap: 14 }}>
          <Input label="agent framing" value={form.agent_framing} onChange={set("agent_framing")} placeholder="an entity on a social network" />
          <Input label="agents" value={form.agent_count} onChange={set("agent_count")} type="number" />
          <Input label="tick limit" value={form.tick_limit} onChange={set("tick_limit")} type="number" />
        </div>

        <SectionLabel>experiment</SectionLabel>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14 }}>
          <Toggle label="ipip grounded" value={form.ipip_grounded} onChange={set("ipip_grounded")} />
          <Input label="random seed" value={form.random_seed} onChange={set("random_seed")} type="number" placeholder="leave blank for random" />
        </div>

        <SectionLabel>notes</SectionLabel>
        <Textarea label="" value={form.notes} onChange={set("notes")} placeholder="Hypothesis, context, what changed..." rows={2} />

        {error && <span style={{ ...mono, fontSize: 10, color: "#ff3ea5" }}>{error}</span>}

        <div style={{ display: "flex", gap: 10 }}>
          <Btn onClick={submit} disabled={saving} color="var(--bg)" border="var(--text-h)" bg="var(--text-h)">
            {saving ? "creating…" : "create run"}
          </Btn>
          <Btn onClick={onClose}>cancel</Btn>
        </div>
      </div>
    </div>
  );
}

const LEVEL_COLOR = { info: "var(--text-dim)", warning: "#fb923c", error: "#fb7185" };

function RunLog({ runId, isRunning, status }) {
  const [events, setEvents] = useState([]);
  const bottomRef = useRef(null);

  const load = () => api.getRunEvents(runId).then(setEvents).catch(() => {});

  // Reset + reload when switching runs
  useEffect(() => { setEvents([]); load(); }, [runId]);

  // Reload whenever status changes (catches fast-failing retries that finish < 5s)
  useEffect(() => { load(); }, [status]);

  // Poll every 5s while running
  useEffect(() => {
    if (!isRunning) return;
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, [isRunning, runId]);

  // Auto-scroll to bottom when new events arrive
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [events.length]);

  if (events.length === 0) return null;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 0, borderTop: "1px solid var(--border)" }}>
      <div style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)", padding: "12px 0 6px" }}>
        run log
      </div>
      <div style={{ maxHeight: 220, overflowY: "auto", display: "flex", flexDirection: "column", gap: 0 }}>
        {events.map(e => (
          <div key={e.id} style={{ display: "flex", gap: 12, alignItems: "baseline", padding: "3px 0", borderBottom: "1px solid var(--border)" }}>
            <span style={{ ...mono, fontSize: 9, color: "var(--text-dim)", flexShrink: 0, width: 36, textAlign: "right" }}>
              {e.tick != null ? `t${e.tick}` : "—"}
            </span>
            <span style={{ ...mono, fontSize: 9, fontWeight: 700, color: LEVEL_COLOR[e.level] ?? "var(--text-dim)", flexShrink: 0, width: 42 }}>
              {e.level}
            </span>
            <span style={{ ...mono, fontSize: 10, color: "var(--text)", lineHeight: 1.5, flex: 1 }}>
              {e.message}
            </span>
            <span style={{ ...mono, fontSize: 9, color: "var(--text-dim)", flexShrink: 0 }}>
              {new Date(e.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}

// ── Run detail panel ──────────────────────────────────────────────────────────
function RunDetail({ run, isRunning, isAdmin, onStart, onStop, onDeleteRequest }) {
  const [pending, setPending] = useState(null);
  const [actionError, setActionError] = useState(null);
  const st = STATUS_STYLE[run.status] ?? STATUS_STYLE.stopped;
  const progress = run.tick_limit ? Math.min(100, Math.round((run.tick_count ?? 0) / run.tick_limit * 100)) : null;

  const handleStart = async () => {
    setPending("starting"); setActionError(null);
    try { await onStart(run.id); } catch (e) { setActionError(e.message); } finally { setPending(null); }
  };
  const handleStop = async () => {
    setPending("stopping"); setActionError(null);
    try { await onStop(run.id); } catch (e) { setActionError(e.message); } finally { setPending(null); }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 16 }}>
        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
            <span style={{ ...mono, fontSize: 16, fontWeight: 700, color: "var(--text-h)" }}>{run.name}</span>
            <span style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "2px 8px", border: `1px solid ${st.color}`, color: st.color }}>
              {st.label}
            </span>
          </div>
          {run.description && (
            <span style={{ ...mono, fontSize: 12, color: "var(--text)", lineHeight: 1.5 }}>{run.description}</span>
          )}
        </div>
        <span style={{ ...mono, fontSize: 11, color: "var(--text-dim)", flexShrink: 0 }}>#{run.id}</span>
      </div>

      {/* Stats row */}
      <div style={{ display: "flex", gap: 24, alignItems: "center", flexWrap: "wrap" }}>
        <span style={{ ...mono, fontSize: 11, color: "var(--text-h)", fontWeight: 700 }}>
          {run.tick_count ?? 0}
          {run.tick_limit ? <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> / {run.tick_limit} ticks</span> : <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> ticks</span>}
        </span>
        <span style={{ ...mono, fontSize: 11, color: "var(--text-h)", fontWeight: 700 }}>
          {run.actual_agent_count ?? run.agent_count ?? 0}
          <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> agents</span>
          {run.actual_agent_count != null && run.agent_count != null && run.actual_agent_count !== run.agent_count && (
            <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> (cfg {run.agent_count})</span>
          )}
        </span>
        <span style={{ ...mono, fontSize: 11, color: "var(--text-h)", fontWeight: 700 }}>
          {run.post_count ?? 0}
          <span style={{ color: "var(--text-dim)", fontWeight: 400 }}> posts</span>
        </span>
        <span style={{ ...mono, fontSize: 11, color: "var(--text-dim)" }}>
          created {run.created_at ? new Date(run.created_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" }) : "—"}
        </span>
      </div>

      {/* Progress bar */}
      {progress !== null && (
        <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
          <div style={{ height: 3, background: "var(--track, var(--border))", borderRadius: 2 }}>
            <div style={{ height: 3, width: `${progress}%`, background: isRunning ? "#2dd4bf" : "var(--text-dim)", borderRadius: 2, transition: "width 0.4s ease" }} />
          </div>
          <span style={{ ...mono, fontSize: 9, color: "var(--text-dim)" }}>
            {progress}% complete{run.started_at && ` · started ${new Date(run.started_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}`}
          </span>
        </div>
      )}

      {/* Config grid */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(140px, 1fr))", gap: 16, padding: "16px 0", borderTop: "1px solid var(--border)", borderBottom: "1px solid var(--border)" }}>
        <FIELD label="model"   value={run.model?.replace(/-latest$/, "")} />
        <FIELD label="news"    value={run.news_enabled ? "enabled" : "disabled"} color={run.news_enabled ? "#2dd4bf" : "#ff3ea5"} />
        <FIELD label="mode"    value={run.batch_mode ? "batch" : "timed"} color={run.batch_mode ? "#c77dff" : null} />
        <FIELD label="ipip"    value={run.ipip_grounded !== false ? "grounded" : "ungrounded"} color={run.ipip_grounded !== false ? "#2dd4bf" : "#fb923c"} />
        {run.post_framing      && <FIELD label="framing"    value={run.post_framing} />}
        {run.persona           && <FIELD label="persona"    value={run.persona} />}
        <FIELD label="seed distribution" value={run.seed_distribution} />
        {run.random_seed != null && <FIELD label="random seed" value={run.random_seed} />}
        {run.ended_at          && <FIELD label="ended"      value={new Date(run.ended_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })} />}
      </div>

      {/* Notes */}
      {run.notes && (
        <div style={{ ...mono, fontSize: 12, color: "var(--text)", lineHeight: 1.7 }}>
          {run.notes}
        </div>
      )}

      {/* Run log */}
      <RunLog runId={run.id} isRunning={isRunning} status={run.status} />

      {/* Actions */}
      {isAdmin && (
        <div style={{ display: "flex", gap: 8, alignItems: "center", justifyContent: "space-between" }}>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            {run.status !== "seeding" && run.status !== "pending" && (
              pending ? (
                <Btn disabled>{pending}…</Btn>
              ) : isRunning ? (
                <Btn onClick={handleStop} color="#fb7185" border="#fb7185">stop</Btn>
              ) : run.status === "stopped" ? (
                <Btn onClick={handleStart} color="var(--text-h)" border="var(--text-h)">resume</Btn>
              ) : run.status === "ready" ? (
                <Btn onClick={handleStart} color="var(--text-h)" border="var(--text-h)">start</Btn>
              ) : run.status === "failed" ? (
                <Btn onClick={handleStart} color="#fb923c" border="#fb923c">retry</Btn>
              ) : null
            )}
            {actionError && <span style={{ ...mono, fontSize: 9, color: "#fb7185" }}>{actionError}</span>}
          </div>
          {!isRunning && (
            <Btn onClick={() => onDeleteRequest(run)} color="var(--text-dim)">delete</Btn>
          )}
        </div>
      )}
    </div>
  );
}

// ── Sidebar run item ──────────────────────────────────────────────────────────
function RunItem({ run, isSelected, isRunning, onClick }) {
  const st = STATUS_STYLE[run.status] ?? STATUS_STYLE.stopped;
  return (
    <button
      onClick={onClick}
      style={{
        ...mono, width: "100%", textAlign: "left",
        padding: "10px 14px", cursor: "pointer",
        border: "none", borderBottom: "1px solid var(--border)",
        background: isSelected ? "var(--border)" : "transparent",
        display: "flex", flexDirection: "column", gap: 4,
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "var(--text-h)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {run.name}
        </span>
        <span style={{ width: 7, height: 7, borderRadius: "50%", background: st.color, flexShrink: 0, animation: isRunning ? "pulse 1.4s ease-in-out infinite" : "none" }} />
      </div>
      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
        <span style={{ fontSize: 9, color: "var(--text-dim)" }}>
          {run.tick_count ?? 0}{run.tick_limit ? ` / ${run.tick_limit}` : ""} ticks
        </span>
        <span style={{ fontSize: 9, color: "var(--text-dim)" }}>·</span>
        <span style={{ fontSize: 9, color: "var(--text-dim)" }}>
          {run.actual_agent_count ?? run.agent_count ?? "?"} agents
        </span>
      </div>
    </button>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Runs() {
  const { runs, runningRunIds, viewingRunId, setViewingRunId, refresh } = useRun();
  const { isAdmin } = useAdmin();
  const [creating, setCreating] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);

  const selectedRun = runs.find(r => r.id === viewingRunId) ?? runs[runs.length - 1] ?? null;

  const handleStart = async (runId) => { await api.startRun(runId);  await refresh(); };
  const handleStop  = async (runId) => { await api.stopRun(runId);   await refresh(); };

  const handleDelete = async () => {
    const run = confirmDelete;
    setConfirmDelete(null);
    try { await api.deleteRun(run.id); await refresh(); } catch (e) { alert(`Failed to delete: ${e.message}`); }
  };

  return (
    <>
      {confirmDelete && (
        <DeleteDialog run={confirmDelete} onConfirm={handleDelete} onCancel={() => setConfirmDelete(null)} />
      )}
      {creating && (
        <CreateRunModal onCreated={async () => { setCreating(false); await refresh(); }} onClose={() => setCreating(false)} />
      )}

      <div style={{ display: "flex", minHeight: "calc(100svh - 120px)" }}>
        {/* ── Sidebar ── */}
        <div style={{ width: 240, flexShrink: 0, borderRight: "1px solid var(--border)", display: "flex", flexDirection: "column", overflow: "hidden" }}>
          {/* Sidebar header */}
          <div style={{ padding: "12px 14px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ ...mono, fontSize: 9, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--text-dim)" }}>
              {runs.length} run{runs.length !== 1 ? "s" : ""}
            </span>
            {isAdmin && (
              <button
                onClick={() => setCreating(true)}
                style={{ ...mono, fontSize: 9, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.1em", padding: "2px 10px", cursor: "pointer", border: "1px solid var(--text-h)", background: "transparent", color: "var(--text-h)" }}
              >
                + new
              </button>
            )}
          </div>
          {/* Run list */}
          <div style={{ overflowY: "auto", flex: 1 }}>
            {[...runs].reverse().map(run => (
              <RunItem
                key={run.id}
                run={run}
                isSelected={run.id === (selectedRun?.id)}
                isRunning={runningRunIds.includes(run.id)}
                onClick={() => setViewingRunId(run.id)}
              />
            ))}
          </div>
        </div>

        {/* ── Detail panel ── */}
        <div style={{ flex: 1, overflowY: "auto", padding: 28 }}>
          {selectedRun ? (
            <RunDetail
              run={selectedRun}
              isRunning={runningRunIds.includes(selectedRun.id)}
              isAdmin={isAdmin}
              onStart={handleStart}
              onStop={handleStop}
              onDeleteRequest={setConfirmDelete}
            />
          ) : (
            <div style={{ ...mono, fontSize: 11, color: "var(--text-dim)", paddingTop: 40, textAlign: "center" }}>
              no runs yet
            </div>
          )}
        </div>
      </div>
    </>
  );
}
