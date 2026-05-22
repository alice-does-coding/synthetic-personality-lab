// Per-trait colours used wherever Big Five (OCEAN) data is rendered —
// agent profile, population drift, social graph, listing pages.
// News.jsx uses TRAIT_COLORS_SOFT for a less saturated palette.

export const TRAITS = [
  "openness",
  "conscientiousness",
  "extraversion",
  "agreeableness",
  "neuroticism",
];

export const TRAIT_COLORS = {
  openness:          "#8b5cf6",
  conscientiousness: "#3b82f6",
  extraversion:      "#f59e0b",
  agreeableness:     "#22c55e",
  neuroticism:       "#ef4444",
};

// Softer variant used on the News page so charts read against a denser layout.
export const TRAIT_COLORS_SOFT = {
  openness:          "#a78bfa",
  conscientiousness: "#818cf8",
  extraversion:      "#f472b6",
  agreeableness:     "#2dd4bf",
  neuroticism:       "#fb7185",
};

// Single-letter abbreviation per trait (compact UI).
export const TRAIT_SHORT = {
  openness:          "O",
  conscientiousness: "C",
  extraversion:      "E",
  agreeableness:     "A",
  neuroticism:       "N",
};

// Three-letter abbreviation per trait (used where O/C/E/A/N is too terse).
export const TRAIT_SHORT3 = {
  openness:          "OPE",
  conscientiousness: "CON",
  extraversion:      "EXT",
  agreeableness:     "AGR",
  neuroticism:       "NEU",
};

// Human-readable label per trait.
export const TRAIT_LABELS = {
  openness:          "Openness",
  conscientiousness: "Conscientiousness",
  extraversion:      "Extraversion",
  agreeableness:     "Agreeableness",
  neuroticism:       "Neuroticism",
};
