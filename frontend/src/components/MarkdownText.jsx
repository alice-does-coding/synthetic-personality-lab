import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

const COMPONENTS = {
  // Paragraphs — no margin, inherit everything from parent
  p: ({ children }) => <span style={{ display: "block" }}>{children}</span>,

  // Bold
  strong: ({ children }) => (
    <strong style={{ fontWeight: 700, color: "var(--text-h)" }}>{children}</strong>
  ),

  // Italic
  em: ({ children }) => (
    <em style={{ fontStyle: "italic", color: "inherit" }}>{children}</em>
  ),

  // Strikethrough
  del: ({ children }) => (
    <del style={{ opacity: 0.5 }}>{children}</del>
  ),

  // Inline code
  code: ({ children }) => (
    <code style={{
      fontFamily: "var(--mono)", fontSize: "0.9em",
      padding: "1px 5px",
      background: "var(--accent-bg)",
      border: "1px solid var(--accent-border)",
      color: "var(--text-h)",
    }}>{children}</code>
  ),

  // Links — open in new tab, pink
  a: ({ href, children }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      style={{ color: "var(--pink)", textDecoration: "none" }}
    >
      {children}
    </a>
  ),

  // Blockquote — left border, muted
  blockquote: ({ children }) => (
    <blockquote style={{
      margin: "6px 0",
      paddingLeft: 10,
      borderLeft: "2px solid var(--fuchsia, #e879f9)",
      color: "var(--text)",
      fontStyle: "italic",
    }}>
      {children}
    </blockquote>
  ),

  // Lists
  ul: ({ children }) => (
    <ul style={{ margin: "4px 0", paddingLeft: 20, listStyleType: "disc" }}>{children}</ul>
  ),
  ol: ({ children }) => (
    <ol style={{ margin: "4px 0", paddingLeft: 20 }}>{children}</ol>
  ),
  li: ({ children }) => (
    <li style={{ marginBottom: 2 }}>{children}</li>
  ),

  // Strip headings down to bold text — agents shouldn't be posting h1s
  h1: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
  h2: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
  h3: ({ children }) => <strong style={{ fontWeight: 700 }}>{children}</strong>,
};

export default function MarkdownText({ children, style }) {
  return (
    <span style={{ display: "block", ...style }}>
      <ReactMarkdown components={COMPONENTS} remarkPlugins={[remarkGfm]}>
        {children ?? ""}
      </ReactMarkdown>
    </span>
  );
}
