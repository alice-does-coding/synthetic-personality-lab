import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";

const TRAIT_COLORS = {
  openness: "#8b5cf6", conscientiousness: "#3b82f6",
  extraversion: "#f59e0b", agreeableness: "#22c55e", neuroticism: "#ef4444",
};

function ThreadPost({ post }) {
  const depth = post.depth ?? 0;
  const time = new Date(post.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });

  return (
    <div style={{
      display: "flex",
      gap: 12,
      paddingLeft: depth * 28,
      position: "relative",
    }}>
      {/* Thread line */}
      {depth > 0 && (
        <div style={{
          position: "absolute",
          left: depth * 28 - 14,
          top: 0, bottom: 0,
          width: 2,
          background: "var(--border)",
        }} />
      )}

      <div style={{ flex: 1 }}>
        <div className="card" style={{ marginBottom: 8 }}>
          <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
            <Link
              to={`/agents/${post.agent_id}`}
              style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", textDecoration: "none" }}
            >
              {post.agent_name}
              <span style={{ fontWeight: 400, color: "var(--text)", marginLeft: 4 }}>
                @{post.agent_handle}
              </span>
            </Link>
            <span className="muted" style={{ fontSize: 12 }}>tick {post.tick_number} · {time}</span>
          </div>
          <p style={{ margin: 0, lineHeight: 1.55, fontSize: 15 }}>{post.content}</p>
        </div>
      </div>
    </div>
  );
}

export default function Thread() {
  const { id } = useParams();
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.thread(id)
      .then(setPosts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const root = posts[0];

  return (
    <div>
      <Link to="/" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
        ← Timeline
      </Link>
      <h2 style={{ fontSize: 15, margin: "12px 0 16px", color: "var(--text-h)" }}>
        Thread · {posts.length} post{posts.length !== 1 ? "s" : ""}
      </h2>
      <div style={{ display: "flex", flexDirection: "column" }}>
        {posts.map((post) => <ThreadPost key={post.id} post={post} />)}
      </div>
    </div>
  );
}
