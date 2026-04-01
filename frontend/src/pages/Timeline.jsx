import { useState, useEffect } from "react";
import { api } from "../api";
import PostCard from "../components/PostCard";

const SORT_OPTIONS = [
  { value: "newest",   label: "Newest" },
  { value: "oldest",   label: "Oldest" },
  { value: "comments", label: "Most replies" },
];

function sort(posts, by) {
  const copy = [...posts];
  if (by === "newest")   return copy.sort((a, b) => new Date(b.created_at) - new Date(a.created_at));
  if (by === "oldest")   return copy.sort((a, b) => new Date(a.created_at) - new Date(b.created_at));
  if (by === "comments") return copy.sort((a, b) => b.reply_count - a.reply_count);
  return copy;
}

export default function Timeline() {
  const [posts,   setPosts]   = useState([]);
  const [error,   setError]   = useState(null);
  const [loading, setLoading] = useState(true);
  const [sortBy,  setSortBy]  = useState("newest");

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

  const sorted = sort(posts, sortBy);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <h1 className="page-title" style={{ margin: 0 }}>Timeline</h1>
        <div style={{ display: "flex", gap: 4 }}>
          {SORT_OPTIONS.map((o) => (
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
      {sorted.length === 0 && <p className="muted">No posts yet — fire a tick to get started.</p>}
      {sorted.map((p) => <PostCard key={p.id} post={p} />)}
    </div>
  );
}
