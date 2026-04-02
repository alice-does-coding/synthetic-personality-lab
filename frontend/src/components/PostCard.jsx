import { Link } from "react-router-dom";

function Headline({ headlines }) {
  const h = headlines[0];
  return (
    <div style={{
      margin: "10px 0 0 0",
      padding: "8px 10px",
      borderLeft: "3px solid var(--accent)",
      background: "var(--bg)",
      borderRadius: "0 6px 6px 0",
    }}>
      <div style={{
        fontSize: 10, fontWeight: 700, color: "var(--accent)",
        textTransform: "uppercase", letterSpacing: "0.5px", marginBottom: 3,
      }}>
        {h.source} · {h.category}
      </div>
      {h.url ? (
        <a
          href={h.url}
          target="_blank"
          rel="noopener noreferrer"
          style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4, textDecoration: "none" }}
        >
          {h.title}
        </a>
      ) : (
        <span style={{ fontSize: 12, color: "var(--text)", lineHeight: 1.4 }}>{h.title}</span>
      )}
    </div>
  );
}

export default function PostCard({ post, depth = 0 }) {
  const time = new Date(post.created_at).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit",
  });

  const threadCount = post.thread_count ?? post.reply_count ?? 0;

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

        {/* reply context */}
        {post.parent_handle && depth === 0 && (
          <div style={{ fontSize: 12, color: "var(--text)", marginBottom: 6, opacity: 0.6 }}>
            ↩ replying to @{post.parent_handle}
          </div>
        )}

        {/* content */}
        <p style={{ margin: 0, lineHeight: 1.55, fontSize: 15 }}>{post.content}</p>

        {/* headline */}
        {post.news_context && post.news_context.length > 0 && (
          <Headline headlines={post.news_context} />
        )}

        {/* footer */}
        <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 10 }}>
          {threadCount > 0 && (
            <Link
              to={`/thread/${post.id}`}
              style={{ fontSize: 12, textDecoration: "none", color: "var(--text)", opacity: 0.7 }}
            >
              💬 {threadCount} {threadCount === 1 ? "comment" : "comments"}
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
