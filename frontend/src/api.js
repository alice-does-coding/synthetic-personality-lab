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
  listAgents:         ()          => req("/agents/"),
  getAgent:           (id)        => req(`/agents/${id}`),
  createAgent:        (body)      => req("/agents/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  personalityHistory: (id)        => req(`/agents/${id}/personality`),
  populationDrift:    ()          => req(`/agents/population`),
  trajectories:       ()          => req(`/agents/trajectories`),
  graph:              ()          => req(`/agents/graph`),
  follow:             (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "POST" }),
  unfollow:           (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "DELETE" }),

  // news
  listNews:                   ()    => req("/news/"),
  newsPosts:                  (id)  => req(`/news/${id}/posts`),
  newsSentimentOverTime:      ()    => req("/news/sentiment-over-time"),
  newsPersonalityCorrelation: ()    => req("/news/personality-correlation"),
  postSentimentOverTime:      ()    => req("/news/post-sentiment-over-time"),
  postPersonalityCorrelation: ()    => req("/news/post-personality-correlation"),
  sentimentContagion:         ()    => req("/news/contagion"),

  // posts
  listPosts:  (limit = 50, agentId) => req(`/posts/?limit=${limit}${agentId ? `&agent_id=${agentId}` : ""}`),
  monologue:  (agentId, limit = 100) => req(`/posts/monologue/${agentId}?limit=${limit}`),
  feed:      (agentId, limit = 20) => req(`/posts/feed/${agentId}?limit=${limit}`),
  replies:   (postId)              => req(`/posts/${postId}/replies`),
  thread:    (postId)              => req(`/posts/${postId}/thread`),
};
