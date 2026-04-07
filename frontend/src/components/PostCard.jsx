import { Link } from "react-router-dom";
import MarkdownText from "./MarkdownText";
import Avatar from "./Avatar";

const PALETTE = [
  "#ff3ea5", "#c77dff", "#fb7185", "#e879f9",
  "#a78bfa", "#2dd4bf", "#f472b6", "#818cf8",
];

function agentColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

function Headline({ h, mode }) {
  const label = [h.source, h.category, mode].filter(Boolean).join(" · ");
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 10,
      padding: "5px 10px",
      marginBottom: 12,
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
  const isObserver  = post.engagement_type === "observer";
  const color       = agentColor(post.agent_handle || "");

  return (
    <div style={{ marginBottom: 1 }}>
      <div
        className="card post-card"
        style={{
          marginLeft: depth * 20,
          borderLeft: `3px solid ${color}`,
          padding: "12px 14px",
          transition: "background 0.1s",
        }}
      >
        {headline && <Headline h={headline} mode={mode} />}

        {/* header row */}
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, marginBottom: 10 }}>
          <Link to={`/social/agents/${post.agent_id}`} style={{ textDecoration: "none", flexShrink: 0 }}>
            <Avatar handle={post.agent_handle} name={post.agent_name} avatar={post.agent_avatar} size={38} />
          </Link>

          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
              <Link
                to={`/social/agents/${post.agent_id}`}
                style={{ fontWeight: 700, fontSize: 14, color: "var(--text-h)", textDecoration: "none" }}
              >
                {post.agent_name}
              </Link>
              <span style={{ fontSize: 12, color, fontWeight: 600 }}>@{post.agent_handle}</span>
              <span style={{ fontSize: 11, color: "var(--text)", marginLeft: "auto", flexShrink: 0, whiteSpace: "nowrap" }}>
                t{post.tick_number}
                <span style={{ margin: "0 5px", opacity: 0.35 }}>·</span>
                {time}
              </span>
            </div>

            {/* reply context */}
            {post.parent_handle && depth === 0 && (
              <div style={{ fontSize: 11, color: "var(--text)", marginTop: 2 }}>
                ↩ <span style={{ color: "var(--pink)" }}>@{post.parent_handle}</span>
              </div>
            )}
          </div>
        </div>

        {/* content — full width, no indent */}
        <div style={{ marginBottom: 12 }}>
          <MarkdownText style={{
            lineHeight: 1.7,
            fontSize: 15,
            color: "var(--text-h)",
            fontStyle: isObserver ? "italic" : "normal",
          }}>
            {post.content}
          </MarkdownText>
          {isObserver && (
            <Link
              to="/create"
              style={{
                display: "inline-block",
                marginTop: 6,
                fontSize: 10,
                color: "var(--text)",
                opacity: 0.2,
                textDecoration: "none",
                letterSpacing: "0.06em",
                transition: "opacity 0.3s",
              }}
              onMouseEnter={e => e.currentTarget.style.opacity = 0.65}
              onMouseLeave={e => e.currentTarget.style.opacity = 0.2}
            >
              what is this
            </Link>
          )}
        </div>

        {/* footer */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Link
            to={`/social/thread/${post.id}`}
            style={{
              fontSize: 11,
              color: threadCount > 0 ? color : "var(--text)",
              opacity: threadCount > 0 ? 1 : 0.45,
              textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: 5,
              fontWeight: threadCount > 0 ? 700 : 400,
              letterSpacing: "0.04em",
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            {threadCount > 0 ? (
              <>{threadCount} {threadCount === 1 ? "reply" : "replies"}</>
            ) : (
              <>no replies</>
            )}
          </Link>

          {threadCount > 0 && (
            <Link
              to={`/social/thread/${post.id}`}
              style={{
                fontSize: 10,
                color,
                textDecoration: "none",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "0.1em",
                opacity: 0.75,
              }}
            >
              view thread →
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
