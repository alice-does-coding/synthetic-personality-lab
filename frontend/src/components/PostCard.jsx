import { Link } from "react-router-dom";
import MarkdownText from "./MarkdownText";
import Avatar from "./Avatar";
import Headline from "./Headline";
import { agentColor } from "../utils/colors";

export default function PostCard({ post, depth = 0 }) {
  const time = new Date(post.created_at).toLocaleTimeString([], {
    hour: "2-digit", minute: "2-digit",
  });

  const replyCount = post.reply_count ?? 0;
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
        </div>

        {/* footer */}
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <Link
            to={`/social/thread/${post.id}`}
            style={{
              fontSize: 11,
              color: replyCount > 0 ? color : "var(--text)",
              opacity: replyCount > 0 ? 1 : 0.45,
              textDecoration: "none",
              display: "inline-flex", alignItems: "center", gap: 5,
              fontWeight: replyCount > 0 ? 700 : 400,
              letterSpacing: "0.04em",
            }}
          >
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="square" strokeLinejoin="miter">
              <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
            </svg>
            {replyCount > 0 ? (
              <>{replyCount} {replyCount === 1 ? "reply" : "replies"}</>
            ) : (
              <>no replies</>
            )}
          </Link>

          {replyCount > 0 && (
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
