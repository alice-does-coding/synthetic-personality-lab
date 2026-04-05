const BASE = import.meta.env.VITE_API_URL ?? "/api";

function getAdminKey() {
  return import.meta.env.VITE_ADMIN_KEY || sessionStorage.getItem("lurkr_admin_key") || "";
}

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function adminReq(path, options = {}) {
  const key = getAdminKey();
  const headers = { ...options.headers };
  if (key) headers["X-Admin-Key"] = key;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // sim
  simStatus:  ()              => req("/sim/status"),
  simTick:    (runId)         => adminReq("/sim/tick",   { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: runId }) }),
  simAssess:  (runId)         => adminReq("/sim/assess", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: runId }) }),

  // agents
  listAgents:         (runId)     => req(`/agents/${runId ? `?run_id=${runId}` : ""}`),
  getAgent:           (id)        => req(`/agents/${id}`),
  createAgent:        (body)      => req("/agents/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  personalityHistory: (id)        => req(`/agents/${id}/personality`),
  populationDrift:    (runId)     => req(`/agents/population${runId ? `?run_id=${runId}` : ""}`),
  trajectories:       (runId)     => req(`/agents/trajectories${runId ? `?run_id=${runId}` : ""}`),
  graph:              (runId)     => req(`/agents/graph${runId ? `?run_id=${runId}` : ""}`),
  follow:             (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "POST" }),
  unfollow:           (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "DELETE" }),

  // news
  listNews:                   (runId) => req(`/news/${runId ? `?run_id=${runId}` : ""}`),
  newsPosts:                  (id)    => req(`/news/${id}/posts`),
  newsSentimentOverTime:      (runId) => req(`/news/sentiment-over-time${runId ? `?run_id=${runId}` : ""}`),
  newsPersonalityCorrelation: (runId) => req(`/news/personality-correlation${runId ? `?run_id=${runId}` : ""}`),
  postSentimentOverTime:      (runId) => req(`/news/post-sentiment-over-time${runId ? `?run_id=${runId}` : ""}`),
  postPersonalityCorrelation: (runId) => req(`/news/post-personality-correlation${runId ? `?run_id=${runId}` : ""}`),
  sentimentContagion:         (runId) => req(`/news/contagion${runId ? `?run_id=${runId}` : ""}`),

  // posts
  listPosts:  (params = {}) => {
    const { limit = 50, agentId, runId, topLevel, tickMin, tickMax, engagementType } = params;
    const q = new URLSearchParams({ limit });
    if (agentId)        q.set("agent_id", agentId);
    if (runId)          q.set("run_id", runId);
    if (topLevel)       q.set("top_level", "true");
    if (tickMin != null) q.set("tick_min", tickMin);
    if (tickMax != null) q.set("tick_max", tickMax);
    if (engagementType) q.set("engagement_type", engagementType);
    return req(`/posts/?${q}`);
  },
  monologue:  (agentId, limit = 100) => req(`/posts/monologue/${agentId}?limit=${limit}`),
  feed:      (agentId, limit = 20) => req(`/posts/feed/${agentId}?limit=${limit}`),
  replies:   (postId)              => req(`/posts/${postId}/replies`),
  thread:    (postId)              => req(`/posts/${postId}/thread`),
  ghostPost: (runId, content)     => adminReq("/posts/ghost", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ run_id: runId, content }) }),

  // runs
  listRuns:    ()        => req("/runs/"),
  listPersonas: ()       => req("/runs/personas"),
  createRun:   (body)    => adminReq("/runs/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  startRun:    (id)      => adminReq(`/runs/${id}/start`,    { method: "POST" }),
  stopRun:     (id)      => adminReq(`/runs/${id}/stop`,     { method: "POST" }),
  deleteRun:   (id)      => adminReq(`/runs/${id}`,          { method: "DELETE" }),
};
