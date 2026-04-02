const BASE = import.meta.env.VITE_API_URL ?? "/api";

async function req(path, options) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json();
}

export const api = {
  // sim
  simStatus:  ()         => req("/sim/status"),
  simStart:   ()         => req("/sim/start",  { method: "POST" }),
  simStop:    ()         => req("/sim/stop",   { method: "POST" }),
  simTick:    ()         => req("/sim/tick",   { method: "POST" }),
  simAssess:  ()         => req("/sim/assess", { method: "POST" }),

  // agents
  listAgents:         ()          => req("/agents/"),
  getAgent:           (id)        => req(`/agents/${id}`),
  createAgent:        (body)      => req("/agents/", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }),
  personalityHistory: (id)        => req(`/agents/${id}/personality`),
  populationDrift:    ()          => req(`/agents/population`),
  follow:             (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "POST" }),
  unfollow:           (from, to)  => req(`/agents/${from}/follow/${to}`, { method: "DELETE" }),

  // news
  listNews:                ()       => req("/news/"),
  newsPosts:               (id)     => req(`/news/${id}/posts`),
  newsSentimentOverTime:   ()       => req("/news/sentiment-over-time"),
  newsPersonalityCorrelation: ()    => req("/news/personality-correlation"),

  // posts
  listPosts: (limit = 50, agentId) => req(`/posts/?limit=${limit}${agentId ? `&agent_id=${agentId}` : ""}`),
  feed:      (agentId, limit = 20) => req(`/posts/feed/${agentId}?limit=${limit}`),
  replies:   (postId)              => req(`/posts/${postId}/replies`),
  thread:    (postId)              => req(`/posts/${postId}/thread`),
};
