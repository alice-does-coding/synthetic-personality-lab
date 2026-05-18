import { createContext, useContext, useState, useEffect } from "react";
import { api } from "./api";

const SimulationContext = createContext(null);

function fetchWithTimeout(promise, ms) {
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("timeout")), ms)
  );
  return Promise.race([promise, timeout]);
}

export function SimulationProvider({ children }) {
  const [simulationRun,    setSimulationRun]    = useState(null);
  const [simulationLoaded, setSimulationLoaded] = useState(false);

  useEffect(() => {
    fetchWithTimeout(api.simulationRun(), 8000)
      .then(setSimulationRun)
      .catch(() => {})
      .finally(() => setSimulationLoaded(true));

    const id = setInterval(() => {
      fetchWithTimeout(api.simulationRun(), 8000).then(setSimulationRun).catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <SimulationContext.Provider value={{
      simulationRun,
      simulationRunId: simulationRun?.id ?? null,
      simulationLoaded,
    }}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  return useContext(SimulationContext);
}
