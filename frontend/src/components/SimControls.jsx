import { useState, useEffect } from "react";
import { api } from "../api";

export default function SimControls() {
  const [status, setStatus]   = useState(null);
  const [loading, setLoading] = useState(false);

  const refresh = () => api.simStatus().then(setStatus).catch(() => {});

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, []);

  const handle = async (action) => {
    setLoading(true);
    try {
      await action();
      await refresh();
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
      {status && (
        <span className="muted" style={{ fontSize: 12 }}>
          tick {status.current_tick}
        </span>
      )}
      {status?.is_running ? (
        <button className="btn" disabled={loading} onClick={() => handle(api.simStop)}>
          ⏸ Pause
        </button>
      ) : (
        <button className="btn primary" disabled={loading} onClick={() => handle(api.simStart)}>
          ▶ Run
        </button>
      )}
      <button className="btn" disabled={loading} onClick={() => handle(api.simTick)}>
        ↪ Tick
      </button>
      <button className="btn" disabled={loading} onClick={() => handle(api.simAssess)}
        title={status ? `~${Math.ceil(status.agents_per_tick / status.rate_limit)}s for ${status.agents_per_tick} agents` : ""}
      >
        📊 Assess
        {status && (
          <span className="muted" style={{ fontSize: 11, marginLeft: 5 }}>
            ~{Math.ceil(status.agents_per_tick / status.rate_limit)}s
          </span>
        )}
      </button>
    </div>
  );
}
