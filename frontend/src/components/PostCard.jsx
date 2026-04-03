import { Link } from "react-router-dom";

const PALETTE = [
  "#ff3ea5", // hot pink
  "#c77dff", // electric purple
  "#fb7185", // rose
  "#e879f9", // fuchsia
  "#a78bfa", // lavender
  "#2dd4bf", // mint
  "#f472b6", // pink
  "#818cf8", // indigo
];

function agentColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function Avatar({ handle }) {
  const letter = (handle || "?")[0].toUpperCase();
  const color  = agentColor(handle || "");
  return (
    <div style={{
      width: 28, height: 28, flexShrink: 0,
      background: color,
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 700, fontSize: 12,
      color: "#000", userSelect: "none",
      fontFamily: "var(--mono)",
    }}>
      {letter}
    </div>
  );
}

function Headline({ h, mode }) {
  const label = [h.source, h.category, mode].filter(Boolean).join(" · ");
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 10,
      padding: "5px 10px",
      marginBottom: 10,
      borderLeft: "2px solid var(--fuchsia, #e879f9)",
      background: "rgba(232,121,249,0.05)",
    }}>
      <span style={{
        fontSize: 10, fontWeight: 700,
        color: "var(--fuchsia, #e879f9)",
        textTransform: "uppercase", letterSpacing: "0.08em",
        whiteSpace: "nowrap", flexShrink: 0,
      }}>
        {label}
      </span>
      {h.url ? (
        <a href={h.url} target="_blank" rel="noopener noreferrer" style={{
          fontSize: 12, color: "var(--text-h)", lineHeight: 1.4,
          textDecoration: "none",
          overflow: "hidden",
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
  const headline    = post.news_context?.[0];
  const mode        = post.engagement_type?.startsWith("news:") ? post.engagement_type.split(":")[1] : null;
  const color       = agentColor(post.agent_handle || "");

  return (
    <div style={{ marginBottom: 1 }}>
      <div
        className="card"
        style={{
          marginLeft: depth * 20,
          borderLeft: depth > 0 ? `2px solid ${color}` : "1px solid var(--border)",
          padding: "12px 16px",
        }}
      >
        {headline && <Headline h={headline} mode={mode} />}

        {/* header row */}
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8 }}>
          <Link to={`/social/agents/${post.agent_id}`} style={{ textDecoration: "none", flexShrink: 0 }}>
            <Avatar handle={post.agent_handle} />
          </Link>

          <Link
            to={`/social/agents/${post.agent_id}`}
            style={{ fontWeight: 700, fontSize: 13, color: "var(--text-h)", textDecoration: "none", flexShrink: 0 }}
          >
            {post.agent_name}
          </Link>

          <span style={{ fontSize: 12, color, fontWeight: 600 }}>@{post.agent_handle}</span>

          <span style={{ fontSize: 11, color: "var(--text)", marginLeft: "auto", flexShrink: 0 }}>
            tick {post.tick_number}
            <span style={{ margin: "0 6px", opacity: 0.4 }}>·</span>
            {time}
          </span>
        </div>

        {/* reply context */}
        {post.parent_handle && depth === 0 && (
          <div style={{ fontSize: 11, color: "var(--text)", marginBottom: 6, paddingLeft: 36 }}>
            ↩ <span style={{ color: "var(--pink)" }}>@{post.parent_handle}</span>
          </div>
        )}

        {/* content */}
        <p style={{
          margin: "0 0 0 36px",
          lineHeight: 1.65,
          fontSize: 14,
          color: "var(--text-h)",
        }}>
          {post.content}
        </p>

        {/* footer */}
        <div style={{ marginTop: 10, paddingLeft: 36 }}>
          <Link
            to={`/social/thread/${post.id}`}
            style={{
              fontSize: 11,
              color: threadCount > 0 ? "var(--pink)" : "var(--text)",
              opacity: threadCount > 0 ? 0.7 : 0.5,
              textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: 5,
              textTransform: "uppercase", letterSpacing: "0.06em",
            }}
          >
            <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            {threadCount} {threadCount === 1 ? "comment" : "comments"}
          </Link>
        </div>
      </div>
    </div>
  );
}
