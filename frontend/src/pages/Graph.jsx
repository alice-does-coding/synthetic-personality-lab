import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import ForceGraph2D from "react-force-graph-2d";
import { api } from "../api";

const TRAITS = ["openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"];
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
  const r  = Math.round(ar + (br - ar) * t);
  const g  = Math.round(ag + (bg - ag) * t);
  const bl = Math.round(ab + (bb - ab) * t);
  return `rgb(${r},${g},${bl})`;
}

function nodeColor(node, trait) {
  const score = node[trait];
  if (score == null) return "#444";
  return lerpColor("#2a2a3a", TRAIT_COLORS[trait], score / 100);
}

const SIZE_MIN = 5;
const SIZE_MAX = 18;

function nodeRadius(node, max) {
  if (max === 0) return SIZE_MIN;
  return SIZE_MIN + ((node.follower_count / max) ** 0.5) * (SIZE_MAX - SIZE_MIN);
}

const SELECT_STYLE = {
  background: "#1a1a1a", border: "1px solid #333", borderRadius: 4,
  color: "#ccc", fontSize: 12, padding: "4px 8px", cursor: "pointer",
};

export default function Graph() {
  const [graphData, setGraphData] = useState({ nodes: [], links: [] });
  const [trait,     setTrait]     = useState("extraversion");
  const [sizeBy,    setSizeBy]    = useState("follower_count");
  const [hovered,   setHovered]   = useState(null);
  const [mousePos,  setMousePos]  = useState({ x: 0, y: 0 });
  const [dims,      setDims]      = useState({ w: 800, h: 600 });
  const [error,     setError]     = useState(null);
  const [loading,   setLoading]   = useState(true);

  const containerRef = useRef(null);
  const graphRef     = useRef(null);
  const navigate     = useNavigate();

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

  // Resize observer — runs after loading resolves and container mounts
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const obs = new ResizeObserver(([entry]) => {
      setDims({ w: entry.contentRect.width, h: entry.contentRect.height });
    });
    obs.observe(el);
    return () => obs.disconnect();
  }, [loading]);

  // Mouse tracking — unconditional, looks up container rect dynamically
  useEffect(() => {
    const onMove = (e) => {
      const rect = containerRef.current?.getBoundingClientRect();
      if (rect) setMousePos({ x: e.clientX - rect.left, y: e.clientY - rect.top });
    };
    window.addEventListener("mousemove", onMove);
    return () => window.removeEventListener("mousemove", onMove);
  }, []);

  const maxFollowers = graphData.nodes.reduce((m, n) => Math.max(m, n.follower_count), 0);
  const maxPosts     = graphData.nodes.reduce((m, n) => Math.max(m, n.post_count), 0);

  // IDs of nodes directly connected to the hovered node
  const connectedIds = useMemo(() => {
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

  const getRadius = useCallback((node) => {
    const max = sizeBy === "follower_count" ? maxFollowers : maxPosts;
    return nodeRadius({ follower_count: node[sizeBy] }, max);
  }, [sizeBy, maxFollowers, maxPosts]);

  const paintNode = useCallback((node, ctx, globalScale) => {
    const r      = getRadius(node);
    const color  = nodeColor(node, trait);
    const isHov  = hovered?.id === node.id;
    const inNet  = !connectedIds || isHov || connectedIds.has(node.id);
    const alpha  = connectedIds && !inNet ? 0.1 : 1;

    if (isHov) {
      ctx.beginPath();
      ctx.arc(node.x, node.y, r + 6, 0, 2 * Math.PI);
      ctx.fillStyle = color.replace("rgb", "rgba").replace(")", ", 0.2)");
      ctx.fill();
    }

    ctx.globalAlpha = alpha;
    ctx.beginPath();
    ctx.arc(node.x, node.y, r, 0, 2 * Math.PI);
    ctx.fillStyle = color;
    ctx.fill();

    if (isHov) {
      ctx.strokeStyle = "#fff";
      ctx.lineWidth = 1.5 / globalScale;
      ctx.stroke();
    }

    if (globalScale >= 1.2 || isHov || inNet) {
      const fontSize = Math.max(10, 12 / globalScale);
      ctx.font = `${isHov ? "600 " : ""}${fontSize}px sans-serif`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillStyle = isHov ? "#fff" : inNet ? "rgba(255,255,255,0.65)" : "rgba(255,255,255,0.15)";
      ctx.fillText(`@${node.handle}`, node.x, node.y + r + fontSize * 0.9);
    }

    ctx.globalAlpha = 1;
  }, [trait, hovered, connectedIds, getRadius]);

  const handleNodeClick = useCallback((node) => {
    navigate(`/agents/${node.id}`);
  }, [navigate]);

  const handleNodeHover = useCallback((node) => {
    setHovered(node || null);
    if (containerRef.current)
      containerRef.current.style.cursor = node ? "pointer" : "default";
  }, []);

  if (loading) return <p className="muted" style={{ padding: 24 }}>Loading…</p>;
  if (error)   return <p className="error"  style={{ padding: 24 }}>{error}</p>;

  const traitColor = TRAIT_COLORS[trait];

  // Keep hover card inside the viewport
  const cardW = 190;
  const cardH = 200;
  const cardX = mousePos.x + 16 + cardW > dims.w ? mousePos.x - cardW - 8 : mousePos.x + 16;
  const cardY = mousePos.y + 16 + cardH > dims.h ? mousePos.y - cardH - 8 : mousePos.y + 16;

  return (
    <div style={{ display: "flex", flexDirection: "column", height: "calc(100vh - 56px)" }}>

      {/* Controls */}
      <div style={{
        display: "flex", alignItems: "center", gap: 16,
        padding: "10px 20px", flexShrink: 0,
        borderBottom: "1px solid var(--border, #222)",
        background: "var(--bg, #0f0f0f)",
      }}>
        <span style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)" }}>Social graph</span>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label className="muted" style={{ fontSize: 12 }}>color</label>
          <div style={{ display: "flex", borderRadius: 4, overflow: "hidden", border: "1px solid #333" }}>
            {TRAITS.map((t, i) => (
              <button key={t} onClick={() => setTrait(t)} style={{
                background: trait === t ? TRAIT_COLORS[t] + "33" : "transparent",
                border: "none",
                borderRight: i < TRAITS.length - 1 ? "1px solid #333" : "none",
                color: trait === t ? TRAIT_COLORS[t] : "#666",
                fontSize: 11, padding: "4px 10px", cursor: "pointer",
                fontWeight: trait === t ? 700 : 400,
                transition: "all 0.15s",
              }}>{t.slice(0, 3).toUpperCase()}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <label className="muted" style={{ fontSize: 12 }}>size</label>
          <div style={{ display: "flex", borderRadius: 4, overflow: "hidden", border: "1px solid #333" }}>
            {[["follower_count", "followers"], ["post_count", "posts"]].map(([val, label]) => (
              <button key={val} onClick={() => setSizeBy(val)} style={{
                background: sizeBy === val ? "#333" : "transparent",
                border: "none", borderRight: val === "follower_count" ? "1px solid #333" : "none",
                color: sizeBy === val ? "#fff" : "#888",
                fontSize: 12, padding: "4px 10px", cursor: "pointer",
              }}>{label}</button>
            ))}
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 6, marginLeft: "auto" }}>
          <span className="muted" style={{ fontSize: 11 }}>0</span>
          <div style={{
            width: 100, height: 10, borderRadius: 5,
            background: `linear-gradient(to right, #2a2a3a, ${traitColor})`,
            border: "1px solid #333",
          }} />
          <span className="muted" style={{ fontSize: 11 }}>100</span>
          <span style={{ fontSize: 11, color: traitColor, marginLeft: 4, fontWeight: 600 }}>{trait}</span>
        </div>

        <button onClick={() => graphRef.current?.zoomToFit(400)} style={{ ...SELECT_STYLE, marginLeft: 8 }}>
          fit view
        </button>
      </div>

      {/* Canvas + hover card */}
      <div ref={containerRef} style={{ flex: 1, background: "#0a0a0f", position: "relative" }}>
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
            const src    = typeof link.source === "object" ? link.source : graphData.nodes.find(n => n.id === link.source);
            const tgt    = typeof link.target === "object" ? link.target : graphData.nodes.find(n => n.id === link.target);
            const srcId  = src?.id;
            const tgtId  = tgt?.id;
            const active = !connectedIds || srcId === hovered?.id || tgtId === hovered?.id;
            const opacity = active ? 0.7 : 0.05;
            return src ? nodeColor(src, trait).replace("rgb", "rgba").replace(")", `, ${opacity})`) : `rgba(255,255,255,${opacity})`;
          }}
          linkWidth={(link) => {
            const srcId = typeof link.source === "object" ? link.source.id : link.source;
            const tgtId = typeof link.target === "object" ? link.target.id : link.target;
            return connectedIds && (srcId === hovered?.id || tgtId === hovered?.id) ? 2.5 : 1.2;
          }}
          linkCurvature={0.2}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          linkDirectionalArrowColor={(link) => {
            const src    = typeof link.source === "object" ? link.source : graphData.nodes.find(n => n.id === link.source);
            const srcId  = src?.id;
            const tgtId  = typeof link.target === "object" ? link.target.id : link.target;
            const active = !connectedIds || srcId === hovered?.id || tgtId === hovered?.id;
            return src ? nodeColor(src, trait).replace("rgb", "rgba").replace(")", `, ${active ? 0.9 : 0.05})`) : "rgba(255,255,255,0.1)";
          }}
        />

        {/* Hover card — follows cursor, stays inside canvas */}
        {hovered && (
          <div style={{
            position: "absolute", left: cardX, top: cardY,
            zIndex: 10, pointerEvents: "none",
            background: "rgba(14,14,18,0.95)",
            border: "1px solid #2a2a2a",
            borderRadius: 8, padding: "12px 14px",
            width: cardW,
            boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
            backdropFilter: "blur(8px)",
          }}>
            <div style={{ fontWeight: 700, fontSize: 13, color: "#fff", marginBottom: 2 }}>
              {hovered.name}
            </div>
            <div className="muted" style={{ fontSize: 11, marginBottom: 10 }}>@{hovered.handle}</div>
            {TRAITS.map(t => (
              <div key={t} style={{ display: "flex", justifyContent: "space-between", fontSize: 11, marginBottom: 3 }}>
                <span style={{ color: TRAIT_COLORS[t], fontWeight: 600 }}>{t.slice(0, 3).toUpperCase()}</span>
                <span style={{ color: "#bbb" }}>{hovered[t] != null ? hovered[t].toFixed(1) : "—"}</span>
              </div>
            ))}
            <div style={{ borderTop: "1px solid #222", marginTop: 8, paddingTop: 8, display: "flex", gap: 10 }}>
              <span className="muted" style={{ fontSize: 10 }}>{hovered.follower_count} followers</span>
              <span className="muted" style={{ fontSize: 10 }}>{hovered.post_count} posts</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
