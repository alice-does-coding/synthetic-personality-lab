import { agentColor } from "../utils/colors";

export default function Avatar({ name, handle, avatar, size = 36 }) {
  const key = handle || name || "?";
  if (avatar) {
    return (
      <div style={{
        width: size, height: size, flexShrink: 0, borderRadius: "50%",
        overflow: "hidden", background: agentColor(key),
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
      background: agentColor(key),
      display: "flex", alignItems: "center", justifyContent: "center",
      fontWeight: 700, fontSize: Math.floor(size * 0.4), color: "#000", userSelect: "none",
    }}>
      {letter}
    </div>
  );
}
