export default function Headline({ h, mode }) {
  const label = [h.source, h.category, mode].filter(Boolean).join(" · ");
  return (
    <div style={{
      display: "flex", alignItems: "baseline", gap: 10,
      padding: "5px 10px", marginBottom: 12,
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
