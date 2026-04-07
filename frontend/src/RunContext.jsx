import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "./api";

const RunContext = createContext(null);

const VIEWING_KEY = "lurkr_viewing_run_id";

export function RunProvider({ children }) {
  const [runs, setRuns] = useState([]);
  const [runningRunIds, setRunningRunIds] = useState([]);
  const [runsLoaded, setRunsLoaded] = useState(false);
  const [viewingRunId, setViewingRunIdState] = useState(null);

  const setViewingRunId = (id) => {
    setViewingRunIdState(id);
    if (id != null) localStorage.setItem(VIEWING_KEY, String(id));
    else localStorage.removeItem(VIEWING_KEY);
  };

  const refresh = useCallback((isInitial = false) => {
    api.listRuns()
      .then(({ runs, running_run_ids }) => {
        setRuns(runs);
        setRunningRunIds(running_run_ids ?? []);

        setViewingRunIdState(prev => {
          // On first load, try to restore from localStorage if still valid
          if (isInitial) {
            const stored = localStorage.getItem(VIEWING_KEY);
            const storedId = stored ? parseInt(stored, 10) : null;
            if (storedId && runs.find(r => r.id === storedId)) return storedId;
          }
          // Keep current selection if still valid
          if (prev && runs.find(r => r.id === prev)) return prev;
          // Fall back to most recently started run
          const started = runs
            .filter(r => r.started_at)
            .sort((a, b) => new Date(b.started_at) - new Date(a.started_at));
          const id = started[0]?.id ?? runs[runs.length - 1]?.id ?? null;
          if (id) localStorage.setItem(VIEWING_KEY, String(id));
          return id;
        });

        setRunsLoaded(true);
      })
      .catch(() => { setRunsLoaded(true); });
  }, []);

  useEffect(() => {
    refresh(true);
    const id = setInterval(() => refresh(false), 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const viewingRun = runs.find(r => r.id === viewingRunId) ?? null;

  return (
    <RunContext.Provider value={{ runs, runningRunIds, runsLoaded, viewingRunId, viewingRun, setViewingRunId, refresh }}>
      {children}
    </RunContext.Provider>
  );
}

export function useRun() {
  return useContext(RunContext);
}
