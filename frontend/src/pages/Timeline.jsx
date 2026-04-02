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

  useEffect(() => {
    load();
    const id = setInterval(load, 8000);
    return () => clearInterval(id);
  }, []);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const sorted = sort(posts, sortBy, trait);

  return (
    <div>
      <div style={{ marginBottom: 20 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
          <h1 className="page-title" style={{ margin: 0 }}>Timeline</h1>
          <div style={{ display: "flex", gap: 4 }}>
            {[
              { value: "latest",    label: "Latest" },
              { value: "discussed", label: "Most discussed" },
              { value: "trait",     label: "By trait" },
            ].map((o) => (
              <button
                key={o.value}
                className={`btn${sortBy === o.value ? " primary" : ""}`}
                onClick={() => setSortBy(o.value)}
              >
                {o.label}
              </button>
            ))}
          </div>
        </div>

        {sortBy === "trait" && (
          <div style={{ display: "flex", gap: 4, justifyContent: "flex-end" }}>
            {TRAITS.map((t) => (
              <button
                key={t.key}
                className={`btn${trait?.key === t.key ? " primary" : ""}`}
                onClick={() => setTrait(t)}
                title={t.label}
              >
                {t.short}
              </button>
            ))}
          </div>
        )}
      </div>

      {sorted.length === 0 && <p className="muted">No posts yet — fire a tick to get started.</p>}
      {sorted.map((p) => <PostCard key={p.id} post={p} />)}
    </div>
  );
}
