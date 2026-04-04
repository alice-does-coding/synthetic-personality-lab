const BASE = import.meta.env.VITE_API_URL ?? "/api";
const ADMIN_KEY = import.meta.env.VITE_ADMIN_KEY;

async function req(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

async function adminReq(path, options = {}) {
  const headers = { ...options.headers };
  if (ADMIN_KEY) headers["X-Admin-Key"] = ADMIN_KEY;
  const res = await fetch(`${BASE}${path}`, { ...options, headers });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // sim
  simStatus:  ()         => req("/sim/status"),
  simStart:   ()         => adminReq("/sim/start",  { method: "POST" }),
  simStop:    ()         => adminReq("/sim/stop",   { method: "POST" }),
  simTick:    ()         => adminReq("/sim/tick",   { method: "POST" }),
  simAssess:  ()         => adminReq("/sim/assess", { method: "POST" }),

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
  listPosts:  (limit = 50, agentId) => req(`/posts/?limit=${limit}${agentId ? `&agent_id=${agentId}` : ""}`),
  monologue:  (agentId, limit = 100) => req(`/posts/monologue/${agentId}?limit=${limit}`),
  feed:      (agentId, limit = 20) => req(`/posts/feed/${agentId}?limit=${limit}`),
  replies:   (postId)              => req(`/posts/${postId}/replies`),
  thread:    (postId)              => req(`/posts/${postId}/thread`),
  ghostPost: (content)            => adminReq("/posts/ghost", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ content }) }),

  // runs
  listRuns:    ()        => req("/runs/"),
  createRun:   (body)    => adminReq("/runs/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  activateRun: (id)      => adminReq(`/runs/${id}/activate`, { method: "POST" }),
  seedRun:     (id)      => adminReq(`/runs/${id}/seed`,     { method: "POST" }),
  startRun:    (id)      => adminReq(`/runs/${id}/start`,    { method: "POST" }),
  stopRun:     (id)      => adminReq(`/runs/${id}/stop`,     { method: "POST" }),
};
