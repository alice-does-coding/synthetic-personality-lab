import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { Link } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api";

const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];
const SHORT  = { openness: "OPE", conscientiousness: "CON", extraversion: "EXT", agreeableness: "AGR", neuroticism: "NEU" };
const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};

function lerpColor(a, b, t) {
  const hex = (s) => parseInt(s, 16);
  const ar = hex(a.slice(1, 3)), ag = hex(a.slice(3, 5)), ab = hex(a.slice(5, 7));
  const br = hex(b.slice(1, 3)), bg = hex(b.slice(3, 5)), bb = hex(b.slice(5, 7));
  return `rgb(${Math.round(ar+(br-ar)*t)},${Math.round(ag+(bg-ag)*t)},${Math.round(ab+(bb-ab)*t)})`;
}

// Normalize score to [0,1] within the actual data range of nodes
function normalizedScore(score, min, max) {
  if (score == null) return 0.5;
  if (max === min) return 0.5;
  return Math.max(0, Math.min(1, (score - min) / (max - min)));
}

function nodeColor(node, trait, traitRange) {
  const score = node[trait];
  if (score == null) return "#555";
  const t = normalizedScore(score, traitRange.min, traitRange.max);
  // Low → muted gray, high → full trait color
  return lerpColor("#888888", TRAIT_COLORS[trait], t);
}

const SIZE_MIN = 5;
const SIZE_MAX = 18;

function nodeRadius(val, max) {
  if (max === 0) return SIZE_MIN;
  return SIZE_MIN + ((val / max) ** 0.5) * (SIZE_MAX - SIZE_MIN);
}

export default function Graph() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [trait,     setTrait]     = useState("extraversion");
  const [sizeBy,    setSizeBy]    = useState("follower_count");
  const [hovered,   setHovered]   = useState(null);
  const [selected,  setSelected]  = useState(null);
  const [mousePos,  setMousePos]  = useState({ x: 0, y: 0 });
  const [dims,      setDims]      = useState({ w: 800, h: 600 });
  const [error,     setError]     = useState(null);
  const [loading,   setLoading]   = useState(true);

  const containerRef = useRef(null);
  const graphRef     = useRef(null);

  useEffect(() => {
    api.graph()
      .then(setGraphData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!graphRef.current || graphData.nodes.length === 0) return;
    graphRef.current.d3Force("charge").strength(-800);
    graphRef.current.d3Force("link").distance(160);
  }, [graphData]);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loading]);

  useEffect(() => {
    const onMove = (e) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  // Compute per-trait min/max across all nodes for normalized coloring
  const traitRanges = useMemo(() => {
    const ranges = {};
    for (const t of TRAITS) {
      const vals = graphData.nodes.map(n => n[t]).filter(v => v != null);
      ranges[t] = {
        min: vals.length ? Math.min(...vals) : 0,
        max: vals.length ? Math.max(...vals) : 100,
      };
    }
    return ranges;
  }, [graphData.nodes]);

  const maxVal = useMemo(() => ({
    follower_count: graphData.nodes.reduce((m, n) => Math.max(m, n.follower_count), 0),
    post_count:     graphData.nodes.reduce((m, n) => Math.max(m, n.post_count), 0),
  }), [graphData.nodes]);

  // Connections for hovered node
  const hoveredConnections = useMemo(() => {
    if (!hovered) return null;
    const ids = new Set();
    graphData.links.forEach((link) => {
      const src = typeof link.source === "object" ? link.source.id : link.source;
      const tgt = typeof link.target === "object" ? link.target.id : link.target;
      if (src === hovered.id) ids.add(tgt);
      if (tgt === hovered.id) ids.add(src);
    });
    return ids;
  }, [hovered, graphData.links]);

  // Connections for selected node (for panel)
  const selectedConnections = useMemo(() => {
    if (!selected) return { followers: [], following: [] };
    const nodeMap = Object.fromEntries(graphData.nodes.map(n => [n.id, n]));
    const followers = [], following = [];
    graphData.links.forEach((link) => {
      const src = typeof link.source === "object" ? link.source.id : link.source;
      const tgt = typeof link.target === "object" ? link.target.id : link.target;
      if (tgt === selected.id && nodeMap[src]) followers.push(nodeMap[src]);
      if (src === selected.id && nodeMap[tgt]) following.push(nodeMap[tgt]);
    });
    return { followers, following };
  }, [selected, graphData.links, graphData.nodes]);

  const getRadius = useCallback((node) => {
    return nodeRadius(node[sizeBy] ?? 0, maxVal[sizeBy]);
  }, [sizeBy, maxVal]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    const r      = getRadius(node);
    const color  = nodeColor(node, trait, traitRanges[trait]);
    const isSel  = selected?.id === node.id;
    const isHov  = hovered?.id === node.id;
    const inNet  = !hoveredConnections || isHov || hoveredConnections.has(node.id);
    const alpha  = hoveredConnections && !inNet ? 0.08 : 1;

    ctx.globalAlpha = alpha;

    if (isSel) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 7, 0, 2 * Math.PI);
      ctx.fillStyle = "#ff3ea533";
      ctx.fill();
    }

    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    if (isSel || isHov) {
      ctx.strokeStyle = isSel ? "#ff3ea5" : "#fff";
      ctx.lineWidth = 1.5 / globalScale;
      ctx.stroke();
    }

    if (isSel || isHov) {
      const fontSize = Math.max(10, 12 / globalScale);
      ctx.font = `700 ${fontSize}px monospace`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = isSel ? "#ff3ea5" : "#fff";
      ctx.fillText(`@${node.handle}`, node.x, node.y + r + fontSize * 0.9);
    }

    ctx.globalAlpha = 1;
  }, [trait, traitRanges, hovered, selected, hoveredConnections, getRadius]);

  const handleNodeClick = useCallback((node) => {
    setSelected(prev => prev?.id === node.id ? null : node);
  }, []);

  const handleNodeHover = useCallback((node) => {
    setHovered(node || null);
    if (containerRef.current)
      containerRef.current.style.cursor = node ? "pointer" : "default";
  }, []);

  if (loading) return <p className="muted" style={{ padding: 24 }}>Loading…</p>;
  if (error)   return <p className="error"  style={{ padding: 24 }}>{error}</p>;

  const traitColor  = TRAIT_COLORS[trait];
  const traitRange  = traitRanges[trait];
  const cardW = 180;
  const cardH = 160;
  const cardX = mousePos.x + 16 + cardW > dims.w ? mousePos.x - cardW - 8 : mousePos.x + 16;
  const cardY = mousePos.y + 16 + cardH > dims.h ? mousePos.y - cardH - 8 : mousePos.y + 16;

  return (
    <div style={{ display: "flex", flexDirection: "column", margin: -20, height: "calc(100vh - 44px)" }}>

      {/* Controls */}
      <div style={{
        display: "flex", alignItems: "center", gap: 10,
        padding: "8px 12px", flexShrink: 0,
        overflowX: "auto", scrollbarWidth: "none",
        borderBottom: "1px solid var(--border)",
        background: "var(--bg)",
      }}>
        <span className="page-title" style={{ margin: 0, flexShrink: 0 }}>Social graph</span>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="muted">color</span>
          <div style={{ display: "flex", border: "1px solid var(--border)" }}>
            {TRAITS.map((t, i) => (
              <button key={t} onClick={() => setTrait(t)} style={{
                background: trait === t ? TRAIT_COLORS[t] + "22" : "var(--bg)",
                border: "none",
                borderRight: i < TRAITS.length - 1 ? "1px solid var(--border)" : "none",
                color: trait === t ? TRAIT_COLORS[t] : "var(--text)",
                fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
                letterSpacing: "0.06em",
                padding: "4px 10px", cursor: "pointer",
              }}>{SHORT[t]}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span className="muted">size</span>
          <div style={{ display: "flex", border: "1px solid var(--border)" }}>
            {[["follower_count", "followers"], ["post_count", "posts"]].map(([val, label], i) => (
              <button key={val} onClick={() => setSizeBy(val)} style={{
                background: sizeBy === val ? "var(--pink)" : "var(--bg)",
                border: "none",
                borderRight: i === 0 ? "1px solid var(--border)" : "none",
                color: sizeBy === val ? "#fff" : "var(--text)",
                fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
                letterSpacing: "0.06em",
                padding: "4px 10px", cursor: "pointer",
              }}>{label}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
          <span className="muted" style={{ fontSize: 10 }}>{Math.round(traitRange.min)}</span>
          <div style={{
            width: 80, height: 8,
            background: `linear-gradient(to right, #888, ${traitColor})`,
            border: "1px solid var(--border)",
          }} />
          <span className="muted" style={{ fontSize: 10 }}>{Math.round(traitRange.max)}</span>
          <span style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color: traitColor, marginLeft: 4 }}>
            {SHORT[trait]}
          </span>
        </div>

        <button className="btn" onClick={() => graphRef.current?.zoomToFit(400)}>fit view</button>
      </div>

      {/* Canvas + panel */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden" }}>
        <div ref={containerRef} style={{ flex: 1, background: "#0a0a0f", position: "relative", overflow: "hidden" }}>
          <ForceGraph2D
            ref={graphRef}
            graphData={graphData}
            width={dims.w}
            height={dims.h}
            backgroundColor="#0a0a0f"
            warmupTicks={80}
            cooldownTicks={200}
            d3AlphaDecay={0.015}
            d3VelocityDecay={0.25}
            onEngineStop={() => graphRef.current?.zoomToFit(400, 60)}
            nodeCanvasObject={paintNode}
            nodePointerAreaPaint={(node, color, ctx) => {
              const r = getRadius(node);
              ctx.beginPath();
              ctx.arc(node.x, node.y, r + 4, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            onNodeClick={handleNodeClick}
            onNodeHover={handleNodeHover}
            linkColor={(link) => {
              const src   = typeof link.source === "object" ? link.source : graphData.nodes.find(n => n.id === link.source);
              const srcId = src?.id;
              const tgtId = typeof link.target === "object" ? link.target.id : link.target;
              const active = !hoveredConnections || srcId === hovered?.id || tgtId === hovered?.id;
              return src
                ? nodeColor(src, trait, traitRanges[trait]).replace("rgb", "rgba").replace(")", `, ${active ? 0.7 : 0.04})`)
                : `rgba(255,255,255,${active ? 0.3 : 0.04})`;
            }}
            linkWidth={(link) => {
              const srcId = typeof link.source === "object" ? link.source.id : link.source;
              const tgtId = typeof link.target === "object" ? link.target.id : link.target;
              return hoveredConnections && (srcId === hovered?.id || tgtId === hovered?.id) ? 2.5 : 1;
            }}
            linkCurvature={0.2}
            linkDirectionalArrowLength={5}
            linkDirectionalArrowRelPos={1}
            linkDirectionalArrowColor={(link) => {
              const src   = typeof link.source === "object" ? link.source : graphData.nodes.find(n => n.id === link.source);
              const srcId = src?.id;
              const tgtId = typeof link.target === "object" ? link.target.id : link.target;
              const active = !hoveredConnections || srcId === hovered?.id || tgtId === hovered?.id;
              return src
                ? nodeColor(src, trait, traitRanges[trait]).replace("rgb", "rgba").replace(")", `, ${active ? 0.9 : 0.04})`)
                : "rgba(255,255,255,0.1)";
            }}
          />

          {/* Hover tooltip — only when nothing selected */}
          {hovered && !selected && (
            <div style={{
              position: "absolute", left: cardX, top: cardY,
              zIndex: 10, pointerEvents: "none",
              background: "var(--bg)", border: "1px solid var(--border)",
              padding: "10px 14px", width: cardW,
            }}>
              <div style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 12, color: "var(--text-h)", marginBottom: 2 }}>
                {hovered.name}
              </div>
              <div className="muted" style={{ fontSize: 11, marginBottom: 8 }}>@{hovered.handle}</div>
              {TRAITS.map(t => (
                <div key={t} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                  <span style={{ fontFamily: "var(--mono)", color: TRAIT_COLORS[t], fontWeight: 700 }}>{SHORT[t]}</span>
                  <span style={{ color: "var(--text-h)" }}>{hovered[t] != null ? Math.round(hovered[t]) : "—"}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Selected node panel */}
        {selected && (
          <div style={{
            width: 260, flexShrink: 0,
            borderLeft: "1px solid var(--border)",
            background: "var(--bg)",
            display: "flex", flexDirection: "column",
            overflowY: "auto",
          }}>
            {/* Header */}
            <div style={{ padding: "14px 16px", borderBottom: "1px solid var(--border)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <div style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 13, color: "var(--text-h)" }}>
                    {selected.name}
                  </div>
                  <div className="muted" style={{ fontSize: 11, marginTop: 2 }}>@{selected.handle}</div>
                </div>
                <button onClick={() => setSelected(null)} style={{
                  background: "none", border: "none", cursor: "pointer",
                  color: "var(--text)", fontFamily: "var(--mono)", fontSize: 14, padding: 0,
                }}>✕</button>
              </div>

              <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
                <div>
                  <div style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 16, color: "var(--text-h)" }}>
                    {selected.follower_count}
                  </div>
                  <div className="muted" style={{ fontSize: 10 }}>followers</div>
                </div>
                <div>
                  <div style={{ fontFamily: "var(--mono)", fontWeight: 700, fontSize: 16, color: "var(--text-h)" }}>
                    {selected.post_count}
                  </div>
                  <div className="muted" style={{ fontSize: 10 }}>posts</div>
                </div>
              </div>

              {/* OCEAN bars */}
              <div style={{ marginTop: 12, display: "flex", flexDirection: "column", gap: 5 }}>
                {TRAITS.map(t => {
                  const val = selected[t] != null ? Math.round(selected[t]) : null;
                  return (
                    <div key={t} style={{ display: "flex", alignItems: "center", gap: 6 }}>
                      <span style={{ fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700, color: TRAIT_COLORS[t], width: 28 }}>
                        {SHORT[t]}
                      </span>
                      <div style={{ flex: 1, height: 3, background: "var(--border)" }}>
                        {val != null && <div style={{ width: `${val}%`, height: "100%", background: TRAIT_COLORS[t] }} />}
                      </div>
                      <span className="muted" style={{ fontSize: 10, width: 20, textAlign: "right" }}>{val ?? "—"}</span>
                    </div>
                  );
                })}
              </div>

              <Link
                to={`/social/agents/${selected.id}`}
                style={{ display: "block", marginTop: 12, fontSize: 11, fontFamily: "var(--mono)", color: "var(--pink)", textDecoration: "none" }}
              >
                view profile →
              </Link>
            </div>

            {/* Followers */}
            <div style={{ padding: "10px 16px", borderBottom: "1px solid var(--border)" }}>
              <div className="page-title" style={{ margin: "0 0 8px" }}>
                followers ({selectedConnections.followers.length})
              </div>
              {selectedConnections.followers.length === 0
                ? <p className="muted" style={{ fontSize: 11 }}>none</p>
                : selectedConnections.followers.map(n => (
                  <NodeRow key={n.id} node={n} trait={trait} traitRange={traitRanges[trait]} onSelect={setSelected} />
                ))
              }
            </div>

            {/* Following */}
            <div style={{ padding: "10px 16px" }}>
              <div className="page-title" style={{ margin: "0 0 8px" }}>
                following ({selectedConnections.following.length})
              </div>
              {selectedConnections.following.length === 0
                ? <p className="muted" style={{ fontSize: 11 }}>none</p>
                : selectedConnections.following.map(n => (
                  <NodeRow key={n.id} node={n} trait={trait} traitRange={traitRanges[trait]} onSelect={setSelected} />
                ))
              }
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function NodeRow({ node, trait, traitRange, onSelect }) {
  const color = nodeColor(node, trait, traitRange);
  const score = node[trait] != null ? Math.round(node[trait]) : null;
  return (
    <div
      onClick={() => onSelect(node)}
      style={{
        display: "flex", alignItems: "center", gap: 8,
        padding: "5px 0", cursor: "pointer",
        borderBottom: "1px solid var(--border)",
      }}
    >
      <div style={{ width: 8, height: 8, background: color, flexShrink: 0 }} />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700, color: "var(--text-h)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
          @{node.handle}
        </div>
      </div>
      {score != null && (
        <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: TRAIT_COLORS[trait], fontWeight: 700 }}>
          {score}
        </span>
      )}
    </div>
  );
}
