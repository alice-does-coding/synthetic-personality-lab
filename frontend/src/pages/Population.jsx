import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import {
  LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";
import { api } from "../api";

const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};
const SHORT = { openness: "O", conscientiousness: "C", extraversion: "E", agreeableness: "A", neuroticism: "N" };

function AgentRadar({ agent }) {
  const p = agent.personality;
  const hasScores = Object.values(p).some((v) => v != null);
  const data = Object.entries(TRAIT_COLORS).map(([trait, color]) => ({
    trait: SHORT[trait],
    value: p[trait] != null ? Math.round(p[trait]) : 0,
    color,
  }));

  return (
    <Link to={`/agents/${agent.id}`} style={{ textDecoration: "none", color: "inherit" }}>
      <div className="card" style={{ cursor: "pointer", textAlign: "center" }}>
        <div style={{ fontWeight: 600, fontSize: 13, color: "var(--text-h)", marginBottom: 1 }}>
          {agent.name}
        </div>
        <div className="muted" style={{ fontSize: 11, marginBottom: 6 }}>@{agent.handle}</div>
        {hasScores ? (
          <>
            <RadarChart width={160} height={140} data={data} style={{ margin: "0 auto" }}>
              <PolarGrid stroke="var(--border)" />
              <PolarAngleAxis
                dataKey="trait"
                tick={({ x, y, payload }) => {
                  const color = TRAIT_COLORS[Object.keys(TRAIT_COLORS).find(k => SHORT[k] === payload.value)];
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

export default function Population() {
  const [agents,     setAgents]     = useState([]);
  const [drift,      setDrift]      = useState([]);
  const [error,      setError]      = useState(null);
  const [loading,    setLoading]    = useState(true);

  useEffect(() => {
    Promise.all([api.listAgents(), api.populationDrift()])
      .then(([a, d]) => { setAgents(a); setDrift(d); })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  return (
    <div>
      <h1 className="page-title" style={{ marginBottom: 20 }}>Population</h1>

      {/* Population mean drift */}
      <div className="card" style={{ marginBottom: 24 }}>
        <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", marginBottom: 4 }}>
          Mean OCEAN drift
        </div>
        <div className="muted" style={{ fontSize: 12, marginBottom: 12 }}>
          Average trait scores across all agents per assessment tick
        </div>
        {drift.length === 0 ? (
          <p className="muted">No assessments yet.</p>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={drift} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
              <XAxis dataKey="tick_number" tick={{ fontSize: 11 }}
                label={{ value: "tick", position: "insideBottomRight", offset: -5, fontSize: 11 }} />
              <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
              <Tooltip
                formatter={(v, name) => [v.toFixed(1), name]}
                labelFormatter={(t) => `tick ${t}`}
              />
              <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize: 12 }} />
              {Object.entries(TRAIT_COLORS).map(([trait, color]) => (
                <Line key={trait} type="monotone" dataKey={trait}
                  stroke={color} strokeWidth={2} dot={{ r: 3 }} activeDot={{ r: 5 }} />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* Agent radar grid */}
      <div style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", marginBottom: 12 }}>
        Agent profiles
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: 10 }}>
        {agents.map((a) => <AgentRadar key={a.id} agent={a} />)}
      </div>
    </div>
  );
}
