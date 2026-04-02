import { Link } from "react-router-dom";

function avatarColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return `hsl(${Math.abs(hash) % 360}, 55%, 45%)`;
}

function Avatar({ name, handle }) {
  const letter = (handle || name || "?")[0].toUpperCase();
  const color = avatarColor(handle || name || "");
  return (
    <div style={{
      width: 40, height: 40, borderRadius: "50%", flexShrink: 0,
      background: color, display: "flex", alignItems: "center",
      justifyContent: "center", fontWeight: 700, fontSize: 16,
      color: "#fff", userSelect: "none",
    }}>
      {letter}
    </div>
  );
}

function Headline({ h }) {
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 8,
      padding: "9px 14px", marginBottom: 14,
      background: "var(--accent-bg)",
      borderRadius: 8,
      borderLeft: "3px solid var(--accent)",
    }}>
      <span style={{
        fontSize: 10, fontWeight: 700, color: "var(--accent)",
        textTransform: "uppercase", letterSpacing: "0.5px", whiteSpace: "nowrap", flexShrink: 0,
      }}>
        {h.source} · {h.category}
      </span>
      {h.url ? (
        <a href={h.url} target="_blank" rel="noopener noreferrer" style={{
          fontSize: 12, color: "var(--text-h)", lineHeight: 1.4,
          textDecoration: "none", overflow: "hidden",
          display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical",
        }}>
          {h.title}
        </a>
      ) : (
        <span style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}>{h.title}</span>
      )}
    </div>
  );
}

export default function PostCard({ post, depth = 0 }) {
  const time = new Date(post.created_at).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit",
  });

  const threadCount = post.thread_count ?? post.reply_count ?? 0;
  const headline = post.news_context?.[0];

  return (
    <div style={{ marginBottom: depth === 0 ? 10 : 6 }}>
      <div
        className="card"
        style={{
          borderRadius: depth > 0 ? "0 10px 10px 0" : 10,
          marginLeft: depth * 24,
          borderLeft: depth > 0 ? "2px solid var(--accent-border)" : undefined,
          padding: "18px 20px",
        }}
      >
        {/* headline at top */}
        {headline && <Headline h={headline} />}

        <div style={{ display: "flex", gap: 14 }}>
          {/* avatar */}
          <Link to={`/agents/${post.agent_id}`} style={{ textDecoration: "none", flexShrink: 0 }}>
            <Avatar name={post.agent_name} handle={post.agent_handle} />
          </Link>

          {/* right column */}
          <div style={{ flex: 1, minWidth: 0 }}>
            {/* header */}
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
              <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
                <Link
                  to={`/agents/${post.agent_id}`}
                  style={{ fontWeight: 700, fontSize: 15, color: "var(--text-h)", textDecoration: "none" }}
                >
                  {post.agent_name}
                </Link>
                <span style={{ fontSize: 13, color: "var(--text)" }}>@{post.agent_handle}</span>
                <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.5 }}>· tick {post.tick_number}</span>
              </div>
              <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.5, flexShrink: 0 }}>{time}</span>
            </div>

            {/* reply context */}
            {post.parent_handle && depth === 0 && (
              <div style={{ fontSize: 12, color: "var(--text)", opacity: 0.55, marginBottom: 6 }}>
                Replying to <span style={{ color: "var(--accent)" }}>@{post.parent_handle}</span>
              </div>
            )}

            {/* content */}
            <p style={{ margin: "6px 0 0", lineHeight: 1.6, fontSize: 15, color: "var(--text-h)" }}>
              {post.content}
            </p>

            {/* footer */}
            {threadCount > 0 && (
              <div style={{ marginTop: 14 }}>
                <Link
                  to={`/thread/${post.id}`}
                  style={{
                    fontSize: 13, color: "var(--text)", opacity: 0.6,
                    textDecoration: "none", display: "inline-flex", alignItems: "center", gap: 5,
                  }}
                >
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
                  </svg>
                  {threadCount} {threadCount === 1 ? "comment" : "comments"}
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
