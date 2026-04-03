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

export default function Timeline() {
  const [posts,   setPosts]   = useState([]);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy,  setSortBy]  = useState("latest");
  const [trait,   setTrait]   = useState(TRAITS[4]);

  useEffect(() => {
    api.listPosts(200)
      .then((all) => setPosts(all.filter((p) => p.parent_id === null)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <p className="muted" style={{ padding: 20 }}>loading…</p>;
  if (error)   return <p className="error"  style={{ padding: 20 }}>{error}</p>;

  const sorted = sort(posts, sortBy, trait);

  return (
    <div>
      {/* controls */}
      <div style={{
        display: "flex", alignItems: "center", gap: 0,
        marginBottom: 16,
        borderBottom: "1px solid var(--border)",
        paddingBottom: 12,
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
            onClick={() => setSortBy(id)}
            style={{
              ...CTRL,
              color:      sortBy === id ? "#000" : "var(--text)",
              background: sortBy === id ? "var(--pink)" : "var(--bg)",
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
              onClick={() => { setSortBy("trait"); setTrait(t); }}
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

      {sorted.length === 0 && <p className="muted">no posts yet.</p>}
      {sorted.map((p) => <PostCard key={p.id} post={p} />)}
    </div>
  );
}
