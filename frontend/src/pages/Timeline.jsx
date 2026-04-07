import { useState, useEffect, useCallback, useRef } from "react";
import { api } from "../api";
import PostCard from "../components/PostCard";
import { useArcade } from "../ArcadeContext";

const TRAITS = [
  { key: "agent_openness",          label: "Openness",          short: "O", color: "#a78bfa" },
  { key: "agent_conscientiousness", label: "Conscientiousness",  short: "C", color: "#818cf8" },
  { key: "agent_extraversion",      label: "Extraversion",       short: "E", color: "#f472b6" },
  { key: "agent_agreeableness",     label: "Agreeableness",      short: "A", color: "#2dd4bf" },
  { key: "agent_neuroticism",       label: "Neuroticism",        short: "N", color: "#fb7185" },
];

function sortPosts(posts, by, trait) {
  const copy = [...posts];
  if (by === "latest")    return copy.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  if (by === "discussed") return copy.sort((a, b) => (b.thread_count ?? b.reply_count ?? 0) - (a.thread_count ?? a.reply_count ?? 0));
  if (by === "trait" && trait) return copy.sort((a, b) => (b[trait.key] ?? 0) - (a[trait.key] ?? 0));
  return copy;
}

const CTRL = {
  display: "inline-flex", alignItems: "center",
  padding: "3px 10px",
  fontSize: 11, fontWeight: 700,
  fontFamily: "var(--mono)",
  textTransform: "uppercase", letterSpacing: "0.08em",
  cursor: "pointer",
  border: "1px solid var(--border)",
  background: "var(--bg)",
  color: "var(--text)",
};

const PAGE_SIZE = 20;
const REFRESH_MS = 15000; // poll every 15s when running

const TICK_WINDOWS = [
  { label: "all",    ticks: null },
  { label: "50t",    ticks: 50   },
  { label: "10t",    ticks: 10   },
  { label: "1t",     ticks: 1    },
];

const ENG_TYPES = [
  { id: null,      label: "all"     },
  { id: "news",    label: "news"    },
  { id: "organic", label: "organic" },
];

export default function Timeline() {
  const { arcadeRunId, arcadeRun, arcadeLoaded } = useArcade();
  const viewingRunId = arcadeRunId;
  const isRunning    = arcadeRun?.status === "running";

  const [posts,        setPosts]        = useState([]);
  const [pending,      setPending]      = useState([]);
  const [error,        setError]        = useState(null);
  const [loading,      setLoading]      = useState(true);
  const [sortBy,       setSortBy]       = useState("latest");
  const [trait,        setTrait]        = useState(TRAITS[4]);
  const [page,         setPage]         = useState(1);
  const [tickWindow,   setTickWindow]   = useState(null);
  const [engType,      setEngType]      = useState(null);
  const [lastRefresh,  setLastRefresh]  = useState(null);

  // Use max_post_tick (actual highest tick with posts) for the window calculation.
  // last_tick can be inflated when the tick counter ran ahead of post generation
  // (e.g. Mistral 401 stopped posts but IPIP tick counter kept going).
  const maxTick    = arcadeRun?.max_post_tick || arcadeRun?.last_tick || 0;
  const maxTickRef = useRef(maxTick);
  maxTickRef.current = maxTick;

  // Track which post IDs are already in the list so background refreshes
  // can identify truly new posts without replacing the whole array.
  const knownIdsRef = useRef(new Set());

  const load = useCallback((resetPage = false) => {
    if (!viewingRunId) return;
    const tickMin = tickWindow != null
      ? Math.max(1, maxTickRef.current - tickWindow + 1)
      : undefined;
    api.listPosts({
      limit: 500,
      runId: viewingRunId,
      topLevel: true,
      tickMin,
      engagementType: engType ?? undefined,
    })
      .then((incoming) => {
        if (resetPage) {
          // Filter change or initial load — replace everything, reset pagination
          knownIdsRef.current = new Set(incoming.map(p => p.id));
          setPosts(incoming);
          setPending([]);
          setPage(1);
        } else {
          // Background refresh — buffer new posts, never touch the visible list
          const newOnes = incoming.filter(p => !knownIdsRef.current.has(p.id));
          if (newOnes.length > 0) {
            newOnes.forEach(p => knownIdsRef.current.add(p.id));
            setPending(prev => [...newOnes, ...prev]);
          }
        }
        setLastRefresh(new Date());
        setError(null);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [viewingRunId, tickWindow, engType]);

  // Reload + reset on filter/run changes
  useEffect(() => {
    setLoading(true);
    load(true);
  }, [load]);

  // Background refresh — never resets page or replaces visible posts
  const intervalRef = useRef(null);
  useEffect(() => {
    if (intervalRef.current) clearInterval(intervalRef.current);
    if (isRunning) {
      intervalRef.current = setInterval(() => load(false), REFRESH_MS);
    }
    return () => clearInterval(intervalRef.current);
  }, [isRunning, load]);

  const flushPending = () => {
    setPosts(prev => [...pending, ...prev]);
    setPending([]);
  };

  if (!arcadeLoaded) return <p className="muted">Loading…</p>;
  if (!arcadeRunId)  return <p className="muted">Arcade not available.</p>;

  const sorted = sortPosts(posts, sortBy, trait);

  const Divider = () => (
    <div style={{ width: 1, height: 18, background: "var(--border)", margin: "0 8px", flexShrink: 0 }} />
  );

  return (
    <div>
      {/* Controls row */}
      <div style={{
        display: "flex", alignItems: "center", flexWrap: "wrap",
        gap: 0, rowGap: 4, paddingBottom: 8,
      }}>
        {/* Sort */}
        <span style={{ fontSize: 11, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.1em", marginRight: 8 }}>sort</span>
        {[
          { id: "latest",    label: "Latest"    },
          { id: "discussed", label: "Hot"       },
        ].map(({ id, label }) => (
          <button
            key={id}
            onClick={() => { setSortBy(id); setPage(1); }}
            style={{
              ...CTRL,
              color:       sortBy === id ? "#000" : "var(--text)",
              background:  sortBy === id ? "var(--pink)" : "var(--bg)",
              borderColor: sortBy === id ? "var(--pink)" : "var(--border)",
              marginRight: 2,
            }}
          >
            {label}
          </button>
        ))}

        <Divider />

        {/* Trait sort */}
        {TRAITS.map((t) => {
          const active = sortBy === "trait" && trait?.key === t.key;
          return (
            <button
              key={t.key}
              onClick={() => { setSortBy("trait"); setTrait(t); setPage(1); }}
              title={t.label}
              style={{
                ...CTRL,
                color:       active ? "#000" : t.color,
                background:  active ? t.color : "var(--bg)",
                borderColor: active ? t.color : "var(--border)",
                marginRight: 2,
                minWidth: 28,
                justifyContent: "center",
              }}
            >
              {t.short}
            </button>
          );
        })}

        <Divider />

        {/* Tick window */}
        <span style={{ fontSize: 11, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.1em", marginRight: 8 }}>ticks</span>
        {TICK_WINDOWS.map(({ label, ticks }) => {
          const active = tickWindow === ticks;
          return (
            <button
              key={label}
              onClick={() => { setTickWindow(ticks); setPage(1); }}
              style={{
                ...CTRL,
                color:       active ? "#000" : "var(--text)",
                background:  active ? "var(--fuchsia)" : "var(--bg)",
                borderColor: active ? "var(--fuchsia)" : "var(--border)",
                marginRight: 2,
              }}
            >
              {label}
            </button>
          );
        })}

        <Divider />

        {/* Engagement type */}
        {ENG_TYPES.map(({ id, label }) => {
          const active = engType === id;
          return (
            <button
              key={label}
              onClick={() => { setEngType(id); setPage(1); }}
              style={{
                ...CTRL,
                color:       active ? "#000" : "var(--text)",
                background:  active ? "var(--accent-border, #444)" : "var(--bg)",
                borderColor: active ? "var(--accent-border, #444)" : "var(--border)",
                marginRight: 2,
              }}
            >
              {label}
            </button>
          );
        })}

        {/* Live indicator + refresh */}
        <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 8 }}>
          {isRunning && (
            <span style={{
              fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
              color: "var(--pink)", textTransform: "uppercase", letterSpacing: "0.1em",
              display: "inline-flex", alignItems: "center", gap: 4,
            }}>
              <span style={{
                width: 6, height: 6, borderRadius: "50%",
                background: "var(--pink)",
                animation: "pulse 1.4s ease-in-out infinite",
              }} />
              live
            </span>
          )}
          {lastRefresh && (
            <span style={{ fontFamily: "var(--mono)", fontSize: 10, color: "var(--text)", opacity: 0.5 }}>
              {lastRefresh.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
            </span>
          )}
          <button
            onClick={() => { setLoading(true); load(); }}
            style={{ ...CTRL, padding: "3px 8px", opacity: 0.7 }}
            title="Refresh"
          >
            ↺
          </button>
        </div>
      </div>

      {/* Post count */}
      <div style={{
        borderBottom: "1px solid var(--border)",
        marginBottom: 16, paddingBottom: 8,
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <span style={{ fontFamily: "var(--mono)", fontSize: 11, color: "var(--text)", opacity: 0.5 }}>
          {loading ? "loading…" : `${sorted.length} post${sorted.length !== 1 ? "s" : ""}`}
          {tickWindow != null && ` · last ${tickWindow} tick${tickWindow !== 1 ? "s" : ""}`}
        </span>
      </div>

      {pending.length > 0 && (
        <button
          onClick={flushPending}
          style={{
            ...CTRL,
            display: "flex", width: "100%", justifyContent: "center",
            marginBottom: 12,
            borderColor: "var(--pink)", color: "var(--pink)",
          }}
        >
          ↑ {pending.length} new post{pending.length !== 1 ? "s" : ""}
        </button>
      )}

      {!loading && sorted.length === 0 && <p className="muted">no posts yet.</p>}
      {sorted.slice(0, page * PAGE_SIZE).map((p) => <PostCard key={p.id} post={p} />)}

      {page * PAGE_SIZE < sorted.length && (
        <button
          onClick={() => setPage((n) => n + 1)}
          style={{
            ...CTRL,
            display: "flex", margin: "16px auto 0",
            color: "var(--text-h)", borderColor: "var(--border)",
          }}
        >
          load more · {sorted.length - page * PAGE_SIZE} remaining
        </button>
      )}
    </div>
  );
}
