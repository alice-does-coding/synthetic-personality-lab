import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";

function avatarColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return `hsl(${Math.abs(hash) % 360}, 55%, 45%)`;
}

function Avatar({ name, handle, size = 36 }) {
  const letter = (handle || name || "?")[0].toUpperCase();
  return (
    <div style={{
      width: size, height: size, borderRadius: "50%", flexShrink: 0,
      background: avatarColor(handle || name || ""),
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 700, fontSize: size * 0.4, color: "#fff", userSelect: "none",
    }}>
      {letter}
    </div>
  );
}

function Headline({ h }) {
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 8,
      padding: "8px 12px", marginBottom: 10,
      background: "var(--accent-bg)", borderRadius: 8,
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
          fontSize: 12, color: "var(--text-h)", lineHeight: 1.4, textDecoration: "none",
          overflow: "hidden", display: "-webkit-box", WebkitLineClamp: 1, WebkitBoxOrient: "vertical",
        }}>
          {h.title}
        </a>
      ) : (
        <span style={{ fontSize: 12, color: "var(--text-h)", lineHeight: 1.4 }}>{h.title}</span>
      )}
    </div>
  );
}

function ThreadPost({ post, descendants, isCollapsed, onToggle }) {
  const depth = post.depth ?? 0;
  const time = new Date(post.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const headline = post.news_context?.[0];
  const hasChildren = descendants > 0;
  const INDENT = 44;

  return (
    <div style={{ display: "flex", marginLeft: depth * INDENT, marginBottom: 6 }}>
      {/* Thread line / collapse toggle */}
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", marginRight: 10, flexShrink: 0 }}>
        <Link to={`/agents/${post.agent_id}`} style={{ textDecoration: "none" }}>
          <Avatar name={post.agent_name} handle={post.agent_handle} size={depth === 0 ? 40 : 34} />
        </Link>
        {hasChildren && (
          <div
            onClick={onToggle}
            title={isCollapsed ? "Expand replies" : "Collapse replies"}
            style={{
              flex: 1, width: 20, marginTop: 6, minHeight: 20,
              display: "flex", justifyContent: "center",
              cursor: "pointer", padding: "0 9px", boxSizing: "border-box",
            }}
            onMouseEnter={e => e.currentTarget.firstChild.style.background = "var(--accent)"}
            onMouseLeave={e => e.currentTarget.firstChild.style.background = isCollapsed ? "var(--accent-border)" : "var(--border)"}
          >
            <div style={{
              width: 2, height: "100%", borderRadius: 2,
              background: isCollapsed ? "var(--accent-border)" : "var(--border)",
              transition: "background 0.15s",
            }} />
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, minWidth: 0, paddingBottom: 4 }}>
        {/* Header */}
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
          <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
            <Link
              to={`/agents/${post.agent_id}`}
              style={{ fontWeight: 700, fontSize: depth === 0 ? 15 : 14, color: "var(--text-h)", textDecoration: "none" }}
            >
              {post.agent_name}
            </Link>
            <span style={{ fontSize: 13, color: "var(--text)" }}>@{post.agent_handle}</span>
            <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.45 }}>· tick {post.tick_number}</span>
          </div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
            {hasChildren && (
              <button
                onClick={onToggle}
                style={{
                  background: "none", border: "none", cursor: "pointer",
                  fontSize: 13, color: "var(--text)", opacity: 0.6, padding: 0,
                  fontFamily: "var(--mono)", fontWeight: 600,
                }}
              >
                {isCollapsed ? `[+${descendants}]` : "[−]"}
              </button>
            )}
            <span style={{ fontSize: 13, color: "var(--text)", opacity: 0.5 }}>{time}</span>
          </div>
        </div>

        {/* Headline */}
        {headline && <Headline h={headline} />}

        {/* Content */}
        {!isCollapsed && (
          <p style={{ margin: 0, lineHeight: 1.6, fontSize: depth === 0 ? 15 : 14, color: "var(--text-h)" }}>
            {post.content}
          </p>
        )}

        {/* Collapsed indicator */}
        {isCollapsed && (
          <p
            onClick={onToggle}
            style={{
              margin: 0, fontSize: 13, color: "var(--accent)", cursor: "pointer", opacity: 0.8,
            }}
          >
            {descendants} {descendants === 1 ? "reply" : "replies"} hidden
          </p>
        )}
      </div>
    </div>
  );
}

function countDescendants(posts, index) {
  const depth = posts[index].depth;
  let count = 0;
  for (let i = index + 1; i < posts.length; i++) {
    if (posts[i].depth <= depth) break;
    count++;
  }
  return count;
}

function getVisible(posts, collapsed) {
  const result = [];
  let hideBelowDepth = null;

  for (let i = 0; i < posts.length; i++) {
    const post = posts[i];

    if (hideBelowDepth !== null) {
      if (post.depth > hideBelowDepth) continue;
      else hideBelowDepth = null;
    }

    const descendants = countDescendants(posts, i);
    const isCollapsed = collapsed.has(post.id);
    result.push({ post, descendants, isCollapsed });
    if (isCollapsed) hideBelowDepth = post.depth;
  }

  return result;
}

export default function Thread() {
  const { id } = useParams();
  const [posts, setPosts] = useState([]);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [collapsed, setCollapsed] = useState(new Set());

  useEffect(() => {
    api.thread(id)
      .then(setPosts)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [id]);

  const toggle = (postId) => {
    setCollapsed((prev) => {
      const next = new Set(prev);
      next.has(postId) ? next.delete(postId) : next.add(postId);
      return next;
    });
  };

  if (loading) return <p className="muted">Loading…</p>;
  if (error)   return <p className="error">{error}</p>;

  const visible = getVisible(posts, collapsed);
  const root = posts[0];
  const replyCount = posts.length - 1;

  return (
    <div>
      <Link to="/" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
        ← Timeline
      </Link>
      <div style={{ margin: "16px 0 24px", display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontSize: 18, fontWeight: 700, color: "var(--text-h)" }}>Comments</span>
        <span className="muted" style={{ fontSize: 13 }}>
          {replyCount === 0 ? "no comments yet" : `${replyCount} ${replyCount === 1 ? "comment" : "comments"}`}
        </span>
      </div>
      <div>
        {visible.map(({ post, descendants, isCollapsed }) => (
          <ThreadPost
            key={post.id}
            post={post}
            descendants={descendants}
            isCollapsed={isCollapsed}
            onToggle={() => toggle(post.id)}
          />
        ))}
      </div>
    </div>
  );
}
