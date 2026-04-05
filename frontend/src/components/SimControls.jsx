import { useState } from "react";
import { api } from "../api";
import { useRun } from "../RunContext";

export default function SimControls() {
  const { viewingRunId, runningRunIds, refresh } = useRun();
  const [loading, setLoading] = useState(false);

  const isRunning = runningRunIds.includes(viewingRunId);

  const handle = async (action) => {
    if (!viewingRunId) return;
    setLoading(true);
    try {
      await action();
      await refresh();
    } finally {
      setLoading(false);
    }
  };

  if (!viewingRunId) return null;

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
      {isRunning ? (
        <button className="btn" disabled={loading} onClick={() => handle(() => api.stopRun(viewingRunId))}>
          ⏸ Stop
        </button>
      ) : (
        <button className="btn primary" disabled={loading} onClick={() => handle(() => api.startRun(viewingRunId))}>
          ▶ Start
        </button>
      )}
      <button className="btn" disabled={loading} onClick={() => handle(() => api.simTick(viewingRunId))}>
        ↪ Tick
      </button>
      <button className="btn" disabled={loading} onClick={() => handle(() => api.simAssess(viewingRunId))}>
        📊 Assess
      </button>
    </div>
  );
}
