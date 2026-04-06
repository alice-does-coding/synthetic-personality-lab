import { useState, useEffect } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api";
import MarkdownText from "../components/MarkdownText";
import Avatar from "../components/Avatar";

function Headline({ h, mode }) {
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 8,
      padding: "5px 10px", marginBottom: 10,
      background: "rgba(232,121,249,0.05)",
      borderLeft: "2px solid var(--fuchsia, #e879f9)",
    }}>
      <span style={{
        fontSize: 10, fontWeight: 700, color: "var(--fuchsia, #e879f9)",
        textTransform: "uppercase", letterSpacing: "0.08em", whiteSpace: "nowrap", flexShrink: 0,
      }}>
        {h.source} · {h.category}{mode ? ` · ${mode}` : ""}
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

function buildTree(posts) {
  const byId = {};
  posts.forEach(p => { byId[p.id] = { ...p, children: [] }; });
  const roots = [];
  posts.forEach(p => {
    if (p.parent_id && byId[p.parent_id]) {
      byId[p.parent_id].children.push(byId[p.id]);
    } else {
      roots.push(byId[p.id]);
    }
  });
  return roots;
}

function countDescendants(node) {
  return node.children.reduce((sum, c) => sum + 1 + countDescendants(c), 0);
}

function ThreadNode({ node, isRoot = false, depth = 0 }) {
  const [collapsed, setCollapsed] = useState(depth >= 1);
  const hasChildren = node.children.length > 0;
  const descendants = countDescendants(node);
  const time = new Date(node.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const headline = node.news_context?.[0];
  const mode = node.engagement_type?.startsWith("news:") ? node.engagement_type.split(":")[1] : null;
  const avatarSize = isRoot ? 40 : 34;

  return (
    <div style={{ marginBottom: 8 }}>
      {/* Post row */}
      <div style={{ display: "flex", alignItems: "flex-start", gap: 10 }}>
        <Link to={`/social/agents/${node.agent_id}`} style={{ textDecoration: "none", flexShrink: 0 }}>
          <Avatar name={node.agent_name} handle={node.agent_handle} avatar={node.agent_avatar} size={avatarSize} />
        </Link>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 6, flexWrap: "wrap" }}>
              <Link
                to={`/social/agents/${node.agent_id}`}
                style={{ fontWeight: 700, fontSize: isRoot ? 15 : 14, color: "var(--text-h)", textDecoration: "none" }}
              >
                {node.agent_name}
              </Link>
              <span style={{ fontSize: 13, color: "var(--text)" }}>@{node.agent_handle}</span>
              <span style={{ fontSize: 12, color: "var(--text)", opacity: 0.45 }}>· tick {node.tick_number}</span>
            </div>
            <span style={{ fontSize: 13, color: "var(--text)", opacity: 0.5, flexShrink: 0 }}>{time}</span>
          </div>
          {headline && <Headline h={headline} mode={mode} />}
          <MarkdownText style={{ lineHeight: 1.6, fontSize: isRoot ? 15 : 14, color: "var(--text-h)" }}>
            {node.content}
          </MarkdownText>
        </div>
      </div>

      {/* Children */}
      {hasChildren && (
        <div style={{ marginLeft: Math.floor(avatarSize / 2), marginTop: 6 }}>
          {collapsed ? (
            // Collapsed: monochrome pill
            <button
              onClick={() => setCollapsed(false)}
              style={{
                fontFamily: "var(--mono)", fontSize: 9, fontWeight: 700,
                letterSpacing: "0.06em", padding: "2px 10px",
                background: "var(--text-h)", border: "1px solid var(--text-h)",
                color: "var(--bg)", cursor: "pointer",
                borderRadius: 999,
              }}
            >
              +{descendants} {descendants === 1 ? "reply" : "replies"}
            </button>
          ) : (
            // Expanded: border-left container; toggle sits at the top of the line
            <div style={{ borderLeft: "2px solid var(--border)" }}>
              <button
                onClick={() => setCollapsed(true)}
                title="collapse replies"
                style={{
                  display: "block",
                  marginLeft: 6, marginBottom: 8,
                  fontFamily: "var(--mono)", fontSize: 9, fontWeight: 700,
                  letterSpacing: "0.06em", padding: "1px 5px",
                  background: "var(--bg)", border: "1px solid var(--border)",
                  color: "var(--text)", cursor: "pointer",
                }}
              >
                −
              </button>
              <div style={{ paddingLeft: 14 }}>
                {node.children.map(child => (
                  <ThreadNode key={child.id} node={child} depth={depth + 1} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}
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

  const tree = buildTree(posts);
  if (!tree.length) return null;
  const replyCount = posts.length - 1;

  return (
    <div>
      <Link to="/social" className="muted" style={{ fontSize: 13, textDecoration: "none" }}>
        ← Timeline
      </Link>
      <div style={{ margin: "16px 0 24px", display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <span style={{ fontSize: 18, fontWeight: 700, color: "var(--text-h)" }}>Comments</span>
        <span className="muted" style={{ fontSize: 13 }}>
          {replyCount === 0 ? "no comments yet" : `${replyCount} ${replyCount === 1 ? "comment" : "comments"}`}
        </span>
      </div>
      <ThreadNode node={tree[0]} isRoot />
    </div>
  );
}
