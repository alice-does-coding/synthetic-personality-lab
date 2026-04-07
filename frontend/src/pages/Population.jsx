import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useRun } from "../RunContext";
import {
  ComposedChart, LineChart, Line, Area,
  XAxis, YAxis, Legend, CartesianGrid, Brush,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  ResponsiveContainer,
} from "recharts";
import { api } from "../api";

const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];
const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};
const SHORT = { openness: "O", conscientiousness: "C", extraversion: "E", agreeableness: "A", neuroticism: "N" };

const AGENT_PALETTE = [
  "#e879f9","#38bdf8","#fb923c","#a3e635","#f472b6",
  "#34d399","#fbbf24","#818cf8","#f87171","#2dd4bf",
];

const CHART_H_SMALL = 260;
const CHART_H_LARGE = 520;

// ── Brush traveller (custom drag handle) ──────────────────────────────────────
function BrushHandle({ x, y, width, height }) {
  const cx = x + width / 2;
  return (
    <g>
      <rect x={x} y={y + 1} width={width} height={height - 2}
        fill="var(--bg)" stroke="var(--border)" strokeWidth={1} />
      {[height * 0.35, height * 0.5, height * 0.65].map((dy, i) => (
        <line key={i} x1={cx - 2} y1={y + dy} x2={cx + 2} y2={y + dy}
          stroke="var(--text)" strokeWidth={1} strokeLinecap="round" />
      ))}
    </g>
  );
}

const BRUSH_PROPS = {
  dataKey: "tick_number",
  height: 22,
  stroke: "var(--border)",
  fill: "var(--bg)",
  travellerWidth: 10,
  traveller: <BrushHandle />,
  tickFormatter: () => "",   // suppress tick labels on the brush itself
};

// ── Modal overlay ─────────────────────────────────────────────────────────────
function Modal({ title, subtitle, onClose, children }) {
  useEffect(() => {
    const esc = (e) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", esc);
    return () => window.removeEventListener("keydown", esc);
  }, [onClose]);

  return (
    <div onClick={onClose} style={{
      position: "fixed", inset: 0, zIndex: 1000,
      background: "rgba(0,0,0,0.8)",
      display: "flex", alignItems: "center", justifyContent: "center",
    }}>
      <div onClick={(e) => e.stopPropagation()} style={{
        background: "var(--bg)",
        border: "1px solid var(--border)",
        padding: "22px 26px",
        width: "94vw", maxHeight: "92vh",
        display: "flex", flexDirection: "column",
      }}>
        <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", marginBottom: 12 }}>
          <div>
            <div style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 11, color: "var(--text-h)", textTransform: "uppercase", letterSpacing: "0.12em" }}>{title}</div>
            {subtitle && <div className="muted" style={{ fontSize: 11, marginTop: 3 }}>{subtitle}</div>}
          </div>
          <button onClick={onClose} style={{
            background: "none", border: "none", cursor: "pointer",
            color: "var(--text)", fontSize: 16, lineHeight: 1,
            padding: "0 0 0 20px", fontFamily: "var(--mono)",
          }}>✕</button>
        </div>
        <div style={{ flex: 1, overflowY: "auto", minHeight: 0 }}>{children}</div>
      </div>
    </div>
  );
}

// ── Expand button ─────────────────────────────────────────────────────────────
const expandBtn = {
  background: "none",
  border: "1px solid var(--border)",
  color: "var(--text)",
  fontFamily: "var(--mono)",
  fontSize: 10,
  fontWeight: 600,
  textTransform: "uppercase",
  letterSpacing: "0.06em",
  cursor: "pointer",
  padding: "2px 8px",
};

// ── Mean drift chart ──────────────────────────────────────────────────────────
function buildMeanData(drift) {
  return drift.map((row) => {
    const out = { tick_number: row.tick_number };
    for (const trait of TRAITS) {
      const lo = Math.max(0,   row[trait] - row[`${trait}_sd`]);
      const hi = Math.min(100, row[trait] + row[`${trait}_sd`]);
      out[trait]            = row[trait];
      out[`${trait}_lo`]   = lo;
      out[`${trait}_band`] = hi - lo;
    }
    return out;
  });
}

function MeanChart({ data, height }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #222)" strokeOpacity={0.6} />
          <XAxis dataKey="tick_number" tick={{ fontSize: 11, fill: "#666" }} tickLine={false} axisLine={{ stroke: "#333" }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#666" }} tickLine={false} axisLine={false} width={32} />
          <Legend
            iconType="plainline" iconSize={16}
            wrapperStyle={{ fontSize: 12, paddingTop: 6 }}
            formatter={(name) => (name.includes("_lo") || name.includes("_band")) ? null : name}
          />
          {TRAITS.map((trait) => {
            const color = TRAIT_COLORS[trait];
            return [
              <Area key={`${trait}_lo`} type="monotone" dataKey={`${trait}_lo`}
                stroke="none" fill="transparent" stackId={trait} legendType="none" dot={false} />,
              <Area key={`${trait}_band`} type="monotone" dataKey={`${trait}_band`}
                stroke="none" fill={color} fillOpacity={0.1} stackId={trait} legendType="none" dot={false} />,
              <Line key={trait} type="monotone" dataKey={trait}
                stroke={color} strokeWidth={2} dot={false} activeDot={false} />,
            ];
          })}
          <Brush {...BRUSH_PROPS} />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function MeanDriftChart({ drift }) {
  const [expanded, setExpanded] = useState(false);
  const data = buildMeanData(drift);
  return (
    <>
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 4 }}>
          <div className="page-title" style={{ margin: 0 }}>Mean OCEAN drift</div>
          <button onClick={() => setExpanded(true)} style={expandBtn}>⤢ expand</button>
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 14 }}>
          Population mean per assessment tick · shading = ±1 SD · drag brush to zoom
        </div>
        <MeanChart data={data} height={CHART_H_SMALL} />
      </div>
      {expanded && (
        <Modal title="Mean OCEAN drift" subtitle="Population mean · shading = ±1 SD · drag brush to zoom" onClose={() => setExpanded(false)}>
          <MeanChart data={data} height={CHART_H_LARGE} />
        </Modal>
      )}
    </>
  );
}

// ── Spaghetti charts ──────────────────────────────────────────────────────────
function buildSpaghettiData(trajectories, trait) {
  const tickMap = {};
  for (const agent of trajectories) {
    for (const snap of agent.snapshots) {
      if (!tickMap[snap.tick_number]) tickMap[snap.tick_number] = { tick_number: snap.tick_number };
      tickMap[snap.tick_number][agent.handle] = snap[trait];
    }
  }
  return Object.values(tickMap).sort((a, b) => a.tick_number - b.tick_number);
}

function SpaghettiChart_({ data, trajectories, agentColors, focused, height }) {
  return (
    <div style={{ height }}>
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 8 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--border, #222)" strokeOpacity={0.6} />
          <XAxis dataKey="tick_number" tick={{ fontSize: 11, fill: "#666" }} tickLine={false} axisLine={{ stroke: "#333" }} />
          <YAxis domain={[0, 100]} tick={{ fontSize: 11, fill: "#666" }} tickLine={false} axisLine={false} width={32} />
          {trajectories.map((agent) => {
            const isFocused = !focused || focused === agent.handle;
            return (
              <Line key={agent.handle} type="monotone" dataKey={agent.handle}
                stroke={agentColors[agent.id]}
                strokeWidth={focused === agent.handle ? 2.5 : isFocused ? 1.5 : 0.5}
                strokeOpacity={isFocused ? 1 : 0.12}
                dot={false} activeDot={false}
              />
            );
          })}
          <Brush {...BRUSH_PROPS} />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function AgentKey({ trajectories, agentColors, focused, onFocus }) {
  const navigate = useNavigate();
  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: "4px 12px", marginBottom: 10 }}>
      {trajectories.map((agent) => (
        <span key={agent.id}
          onClick={(e) => {
            if (e.metaKey || e.ctrlKey) navigate(`/social/agents/${agent.id}`);
            else onFocus(focused === agent.handle ? null : agent.handle);
          }}
          title="Click to isolate · ⌘-click to open agent"
          style={{
            fontSize: 11, fontWeight: 600, cursor: "pointer",
            color: agentColors[agent.id],
            opacity: !focused || focused === agent.handle ? 1 : 0.3,
            textDecoration: focused === agent.handle ? "underline" : "none",
            transition: "opacity 0.15s",
            userSelect: "none",
          }}
        >
          @{agent.handle}
        </span>
      ))}
    </div>
  );
}

function SpaghettiChart({ trait, trajectories, agentColors }) {
  const [expanded, setExpanded] = useState(false);
  const [focused,  setFocused]  = useState(null);
  const data  = buildSpaghettiData(trajectories, trait);
  const title = trait.charAt(0).toUpperCase() + trait.slice(1);
  const color = TRAIT_COLORS[trait];

  return (
    <>
      <div className="card">
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 6 }}>
          <div className="page-title" style={{ margin: 0, color }}>{title}</div>
          <button onClick={() => setExpanded(true)} style={expandBtn}>⤢ expand</button>
        </div>
        <AgentKey trajectories={trajectories} agentColors={agentColors} focused={focused} onFocus={setFocused} />
        <SpaghettiChart_ data={data} trajectories={trajectories} agentColors={agentColors} focused={focused} height={CHART_H_SMALL} />
        <div className="muted" style={{ fontSize: 10, marginTop: 6 }}>
          click handle to isolate · ⌘-click to open profile · drag brush to zoom
        </div>
      </div>
      {expanded && (
        <Modal title={title} subtitle="Individual agent trajectories" onClose={() => setExpanded(false)}>
          <AgentKey trajectories={trajectories} agentColors={agentColors} focused={focused} onFocus={setFocused} />
          <SpaghettiChart_ data={data} trajectories={trajectories} agentColors={agentColors} focused={focused} height={CHART_H_LARGE} />
        </Modal>
      )}
    </>
  );
}

// ── Agent radar ───────────────────────────────────────────────────────────────
function AgentRadar({ agent }) {
  const p = agent.personality;
  const hasScores = Object.values(p).some((v) => v != null);
  const data = TRAITS.map((trait) => ({
    trait: SHORT[trait],
    value: p[trait] != null ? Math.round(p[trait]) : 0,
    color: TRAIT_COLORS[trait],
  }));

  return (
    <Link to={`/social/agents/${agent.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={{ cursor: "pointer", textAlign: "center" }}>
        <div style={{ fontWeight: 700, fontSize: 13, color: "var(--text-h)", marginBottom: 1 }}>{agent.name}</div>
        <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>@{agent.handle}</div>
        {hasScores ? (
          <>
            <RadarChart width={160} height={140} data={data} style={{ margin: "0 auto" }}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis dataKey="trait"
                tick={({ x, y, payload }) => {
                  const color = TRAIT_COLORS[TRAITS.find(k => SHORT[k] === payload.value)];
                  return (
                    <text x={x} y={y} fill={color} textAnchor="middle" dominantBaseline="central" fontSize={10} fontWeight={700}>
                      {payload.value}
                    </text>
                  );
                }}
              />
              <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
              <Radar dataKey="value" stroke="var(--accent)" fill="var(--accent)" fillOpacity={0.2} strokeWidth={1.5} />
            </RadarChart>
            <div style={{ display: "flex", justifyContent: "center", gap: 6, flexWrap: "wrap", marginTop: 4 }}>
              {data.map(({ trait, value, color }) => (
                <span key={trait} style={{ fontSize: 10, fontWeight: 700, color }}>{trait} {value}</span>
              ))}
            </div>
          </>
        ) : (
          <p className="muted" style={{ fontSize: 12, margin: "20px 0" }}>no assessments yet</p>
        )}
        {agent.snapshot_count > 0 && (
          <div className="muted" style={{ fontSize: 10, marginTop: 6 }}>{agent.snapshot_count} assessments</div>
        )}
      </div>
    </Link>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────
export default function Population() {
  const { viewingRunId, runsLoaded } = useRun();
  const [agents,       setAgents]       = useState([]);
  const [drift,        setDrift]        = useState([]);
  const [trajectories, setTrajectories] = useState([]);
  const [error,        setError]        = useState(null);
  const [loading,      setLoading]      = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([api.listAgents(viewingRunId), api.populationDrift(viewingRunId), api.trajectories(viewingRunId)])
      .then(([a, d, t]) => { setAgents(a); setDrift(d); setTrajectories(t); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [viewingRunId]);

  if (!runsLoaded)   return <p className="muted">Loading…</p>;
  if (!viewingRunId) return <p className="muted">No run selected.</p>;
  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const agentColors = {};
  trajectories.forEach((agent, i) => {
    agentColors[agent.id] = AGENT_PALETTE[i % AGENT_PALETTE.length];
  });

  const hasTrajectories = trajectories.some(t => t.snapshots.length > 0);

  return (
    <div>
      <h1 className="page-title" style={{ marginBottom: 20 }}>Drift</h1>

      {drift.length > 0 && <MeanDriftChart drift={drift} />}

      {hasTrajectories && (
        <div style={{ marginBottom: 24 }}>
          <div className="page-title" style={{ marginBottom: 4 }}>
            Individual trajectories
          </div>
          <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
            One line per agent · click handle to isolate · ⌘-click to open profile · drag brush to zoom
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))", gap: 12 }}>
            {TRAITS.map((trait) => (
              <SpaghettiChart key={trait} trait={trait} trajectories={trajectories} agentColors={agentColors} />
            ))}
          </div>
        </div>
      )}

      <div className="page-title" style={{ marginBottom: 12 }}>
        Agent profiles
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
        {agents.map((a) => <AgentRadar key={a.id} agent={a} />)}
      </div>
    </div>
  );
}
