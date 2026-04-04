import { createContext, useContext, useState, useEffect, useCallback } from "react";
import { api } from "./api";

const RunContext = createContext(null);

export function RunProvider({ children }) {
  const [runs, setRuns] = useState([]);
  const [activeRunId, setActiveRunId] = useState(null);
  const [currentTick, setCurrentTick] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  const refresh = useCallback(() => {
    api.listRuns()
      .then(({ runs, active_run_id, current_tick, is_running }) => {
        setRuns(runs);
        setActiveRunId(active_run_id ?? null);
        setCurrentTick(current_tick ?? null);
        setIsRunning(is_running ?? false);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 5000);
    return () => clearInterval(id);
  }, [refresh]);

  const activeRun = runs.find(r => r.id === activeRunId) ?? null;

  return (
    <RunContext.Provider value={{ runs, activeRunId, activeRun, currentTick, isRunning, refresh }}>
      {children}
    </RunContext.Provider>
  );
}

export function useRun() {
  return useContext(RunContext);
}
