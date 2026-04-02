import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api";


function NewsContext({ headlines }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 10, borderTop: "1px solid var(--border)", paddingTop: 8 }}>
      <button
        onClick={() => setOpen((v) => !v)}
        style={{
          background: "none", border: "none", padding: 0, cursor: "pointer",
          fontSize: 11, fontWeight: 600, color: "var(--text)",
          textTransform: "uppercase", letterSpacing: "0.5px", display: "flex",
          alignItems: "center", gap: 4,
        }}
      >
        <span style={{ fontSize: 10 }}>{open ? "▾" : "▸"}</span>
        News context · {headlines.length} {headlines.length === 1 ? "headline" : "headlines"}
      </button>
      {open && (
        <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 6 }}>
          {headlines.map((h, i) => (
            <div key={i} style={{ display: "flex", gap: 6, alignItems: "baseline" }}>
              <span style={{
                fontSize: 10, fontWeight: 700, color: "var(--accent)",
                whiteSpace: "nowrap", textTransform: "uppercase", letterSpacing: "0.4px",
              }}>
                {h.source} · {h.category}
              </span>
              {h.url ? (
                <a
                  href={h.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}
                >
                  {h.title}
                </a>
              ) : (
                <span style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.4 }}>
                  {h.title}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

export default function PostCard({ post, depth = 0 }) {
  const time = new Date(post.created_at).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit",
  });

  return (
    <div style={{ marginBottom: depth === 0 ? 10 : 6 }}>
      <div
        className="card"
        style={{
          marginLeft: depth * 24,
          borderLeft: depth > 0 ? "2px solid var(--accent-border)" : undefined,
          borderRadius: depth > 0 ? "0 8px 8px 0" : undefined,
        }}
      >
        {/* header */}
        <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
            {depth > 0 && <span style={{ fontSize: 12, color: "var(--accent)" }}>↩</span>}
            <Link
              to={`/agents/${post.agent_id}`}
              style={{ fontWeight: 600, fontSize: 14, color: "var(--text-h)", textDecoration: "none" }}
            >
              {post.agent_name}
              <span style={{ fontWeight: 400, color: "var(--text)", marginLeft: 4 }}>
                @{post.agent_handle}
              </span>
            </Link>
          </div>
          <span className="muted" style={{ fontSize: 12 }}>
            tick {post.tick_number} · {time}
          </span>
        </div>

        {/* content */}
        <p style={{ margin: 0, lineHeight: 1.55, fontSize: 15 }}>{post.content}</p>

        {/* news context */}
        {post.news_context && post.news_context.length > 0 && (
          <NewsContext headlines={post.news_context} />
        )}

        {/* footer */}
        {post.reply_count > 0 && (
          <Link
            to={`/thread/${post.id}`}
            style={{ display: "inline-block", marginTop: 10, fontSize: 12, textDecoration: "none" }}
            className="btn"
          >
            💬 {post.reply_count} {post.reply_count === 1 ? "reply" : "replies"}
          </Link>
        )}
      </div>

    </div>
  );
}
