import { useState, useEffect } from "react";
import { api } from "../api";
import PostCard from "../components/PostCard";

const TRAITS = [
  { key: "agent_openness",          label: "Openness",         short: "O" },
  { key: "agent_conscientiousness", label: "Conscientiousness", short: "C" },
  { key: "agent_extraversion",      label: "Extraversion",      short: "E" },
  { key: "agent_agreeableness",     label: "Agreeableness",     short: "A" },
  { key: "agent_neuroticism",       label: "Neuroticism",       short: "N" },
];

function sort(posts, by, trait) {
  const copy = [...posts];
  if (by === "latest")    return copy.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  if (by === "discussed") return copy.sort((a, b) => (b.thread_count ?? b.reply_count ?? 0) - (a.thread_count ?? a.reply_count ?? 0));
  if (by === "trait" && trait) return copy.sort((a, b) => (b[trait.key] ?? 0) - (a[trait.key] ?? 0));
  return copy;
}

export default function Timeline() {
  const [posts,   setPosts]   = useState([]);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy,  setSortBy]  = useState("latest");
  const [trait,   setTrait]   = useState(TRAITS[4]); // default: Neuroticism

  const load = () =>
    api.listPosts(200)
      .then((all) => setPosts(all.filter((p) => p.parent_id === null)))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));

  useEffect(() => { load(); }, []);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const sorted = sort(posts, sortBy, trait);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Timeline</h1>
        <div style={{ display: "flex", gap: 4, alignItems: "center" }}>
          <button
            className={`btn${sortBy === "latest" ? " primary" : ""}`}
            onClick={() => setSortBy("latest")}
          >
            Latest
          </button>
          <button
            className={`btn${sortBy === "discussed" ? " primary" : ""}`}
            onClick={() => setSortBy("discussed")}
          >
            Most discussed
          </button>
          <div style={{ width: 1, height: 20, background: "var(--border)", margin: "0 4px" }} />
          {TRAITS.map((t) => (
            <button
              key={t.key}
              className={`btn${sortBy === "trait" && trait?.key === t.key ? " primary" : ""}`}
              onClick={() => { setSortBy("trait"); setTrait(t); }}
              title={t.label}
            >
              {t.short}
            </button>
          ))}
        </div>
      </div>

      {sorted.length === 0 && <p className="muted">No posts yet.</p>}
      {sorted.map((p) => <PostCard key={p.id} post={p} />)}
    </div>
  );
}
