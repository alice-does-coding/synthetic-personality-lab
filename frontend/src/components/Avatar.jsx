const PALETTE = ["#ff3ea5","#c77dff","#fb7185","#e879f9","#a78bfa","#2dd4bf","#f472b6","#818cf8"];

function avatarColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) hash = str.charCodeAt(i) + ((hash << 5) - hash);
  return PALETTE[Math.abs(hash) % PALETTE.length];
}

export default function Avatar({ name, handle, avatar, size = 36 }) {
  const key = handle || name || "?";
  if (avatar) {
    return (
      <div style={{
        width: size, height: size, flexShrink: 0, borderRadius: "50%",
        overflow: "hidden", background: avatarColor(key),
      }}>
        <img
          src={avatar}
          alt={key}
          style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
        />
      </div>
    );
  }
  const letter = key[0].toUpperCase();
  return (
    <div style={{
      width: size, height: size, flexShrink: 0,
      background: avatarColor(key),
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 700, fontSize: Math.floor(size * 0.4), color: "#000", userSelect: "none",
    }}>
      {letter}
    </div>
  );
}
