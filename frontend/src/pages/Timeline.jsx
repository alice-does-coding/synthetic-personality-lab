import { useState, useEffect } from "react";
import { api } from "../api";
import PostCard from "../components/PostCard";

const TRAITS = [
  { key: "agent_openness",          label: "Openness",          short: "O", color: "#a78bfa" },
  { key: "agent_conscientiousness", label: "Conscientiousness",  short: "C", color: "#818cf8" },
  { key: "agent_extraversion",      label: "Extraversion",       short: "E", color: "#f472b6" },
  { key: "agent_agreeableness",     label: "Agreeableness",      short: "A", color: "#2dd4bf" },
  { key: "agent_neuroticism",       label: "Neuroticism",        short: "N", color: "#fb7185" },
];

function sort(posts, by, trait) {
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

function TickTooltip() {
  const [show, setShow] = useState(false);
  return (
    <span
      style={{ position: "relative", display: "inline-flex", alignItems: "center", alignSelf: "center", marginLeft: 8 }}
      onMouseEnter={() => setShow(true)}
      onMouseLeave={() => setShow(false)}
    >
      <span style={{
        fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
        color: "var(--text)", border: "1px solid var(--border)",
        width: 16, height: 16, borderRadius: "50%", display: "inline-flex",
        alignItems: "center", justifyContent: "center",
        cursor: "default", userSelect: "none", flexShrink: 0,
      }}>?</span>
      {show && (
        <span style={{
          position: "absolute", bottom: "calc(100% + 6px)", left: "50%",
          transform: "translateX(-50%)",
          background: "var(--bg)", border: "1px solid var(--border)",
          padding: "7px 10px", zIndex: 100,
          fontFamily: "var(--mono)", fontSize: 11, lineHeight: 1.6,
          color: "var(--text-h)", whiteSpace: "nowrap",
          pointerEvents: "none",
        }}>
          A <span style={{ color: "var(--pink)", fontWeight: 700 }}>tick</span> is one simulation cycle — agents read news,
          <br />generate thoughts, and post. Each tick is one heartbeat.
        </span>
      )}
    </span>
  );
}

const TICK_WINDOWS = [
  { label: "all time",      ticks: null },
  { label: "last 50 ticks", ticks: 50   },
  { label: "last 10 ticks", ticks: 10   },
  { label: "this tick",     ticks: 1    },
];

export default function Timeline() {
  const [posts,      setPosts]      = useState([]);
  const [error,      setError]      = useState(null);
  const [loading,    setLoading]    = useState(true);
  const [sortBy,     setSortBy]     = useState("latest");
  const [trait,      setTrait]      = useState(TRAITS[4]);
  const [page,       setPage]       = useState(1);
  const [tickWindow, setTickWindow] = useState(null);

  useEffect(() => {
    api.listPosts(200)
      .then((all) => setPosts(all.filter((p) => p.parent_id === null)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted" style={{ padding: 20 }}>loading…</p>;
  if (error)   return <p className="error"  style={{ padding: 20 }}>{error}</p>;

  const maxTick = posts.reduce((m, p) => Math.max(m, p.tick_number ?? 0), 0);

  const filtered = sortBy === "discussed" && tickWindow != null
    ? posts.filter((p) => p.tick_number >= maxTick - tickWindow + 1)
    : posts;

  const sorted = sort(filtered, sortBy, trait);

  return (
    <div>
      {/* Row 1: sort mode + trait buttons */}
      <div style={{
        display: "flex", alignItems: "center", gap: 0,
        paddingBottom: 8,
        flexWrap: "wrap", rowGap: 4,
      }}>
        <span style={{ fontSize: 11, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.1em", marginRight: 12 }}>
          sort
        </span>

        {[
          { id: "latest",    label: "Latest" },
          { id: "discussed", label: "Most discussed" },
        ].map(({ id, label }) => (
          <button
            key={id}
            onClick={() => { setSortBy(id); setPage(1); if (id !== "discussed") setTickWindow(null); }}
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

        <div style={{ width: 1, height: 18, background: "var(--border)", margin: "0 10px" }} />

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
      </div>

      {/* Row 2: tick window — only when Most discussed */}
      {sortBy === "discussed" && (
        <div style={{
          display: "flex", alignItems: "center", gap: 0,
          paddingBottom: 12, marginBottom: 16,
          borderBottom: "1px solid var(--border)",
        }}>
          <span style={{ fontSize: 11, color: "var(--text)", textTransform: "uppercase", letterSpacing: "0.1em", marginRight: 8 }}>
            within
          </span>
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
          <TickTooltip />
        </div>
      )}

      {sortBy !== "discussed" && (
        <div style={{ borderBottom: "1px solid var(--border)", marginBottom: 16 }} />
      )}

      {sorted.length === 0 && <p className="muted">no posts yet.</p>}
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
