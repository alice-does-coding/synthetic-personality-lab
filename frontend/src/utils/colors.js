// Avatar / agent-name colour hashing. Imported by Avatar and PostCard.

const PALETTE = [
  "#ff3ea5", "#c77dff", "#fb7185", "#e879f9",
  "#a78bfa", "#2dd4bf", "#f472b6", "#818cf8",
];

export function agentColor(str) {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    hash = str.charCodeAt(i) + ((hash << 5) - hash);
  }
  return PALETTE[Math.abs(hash) % PALETTE.length];
}
