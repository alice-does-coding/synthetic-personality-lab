import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "./api";

const RunContext = createContext(null);

const VIEWING_KEY = "lurkr_viewing_run_id";

export function RunProvider({ children }) {
  const [runs, setRuns] = useState([]);
  const [runningRunIds, setRunningRunIds] = useState([]);
  const [viewingRunId, setViewingRunIdState] = useState(() => {
    const stored = localStorage.getItem(VIEWING_KEY);
    return stored ? parseInt(stored, 10) : null;
  });

  const setViewingRunId = (id) => {
    setViewingRunIdState(id);
    if (id != null) localStorage.setItem(VIEWING_KEY, String(id));
    else localStorage.removeItem(VIEWING_KEY);
  };

  const refresh = useCallback(() => {
    api.listRuns()
      .then(({ runs, running_run_ids }) => {
        setRuns(runs);
        setRunningRunIds(running_run_ids ?? []);

        // Default to most recently started run; keep current selection if still valid
        setViewingRunIdState(prev => {
          if (prev && runs.find(r => r.id === prev)) return prev;
          const started = runs
            .filter(r => r.started_at)
            .sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
          const id = started[0]?.id ?? runs[runs.length - 1]?.id ?? null;
          if (id) localStorage.setItem(VIEWING_KEY, String(id));
          return id;
        });
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const viewingRun = runs.find(r => r.id === viewingRunId) ?? null;

  return (
    <RunContext.Provider value={{ runs, runningRunIds, viewingRunId, viewingRun, setViewingRunId, refresh }}>
      {children}
    </RunContext.Provider>
  );
}

export function useRun() {
  return useContext(RunContext);
}
