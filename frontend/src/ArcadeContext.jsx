import { createContext, useContext, useState, useEffect } from "react";
import { api } from "./api";

const ArcadeContext = createContext(null);

function fetchWithTimeout(promise, ms) {
  const timeout = new Promise((_, reject) =>
    setTimeout(() => reject(new Error("timeout")), ms)
  );
  return Promise.race([promise, timeout]);
}

export function ArcadeProvider({ children }) {
  const [arcadeRun,    setArcadeRun]    = useState(null);
  const [arcadeLoaded, setArcadeLoaded] = useState(false);

  useEffect(() => {
    fetchWithTimeout(api.arcadeRun(), 8000)
      .then(setArcadeRun)
      .catch(() => {})
      .finally(() => setArcadeLoaded(true));

    const id = setInterval(() => {
      fetchWithTimeout(api.arcadeRun(), 8000).then(setArcadeRun).catch(() => {});
    }, 5000);
    return () => clearInterval(id);
  }, []);

  return (
    <ArcadeContext.Provider value={{
      arcadeRun,
      arcadeRunId: arcadeRun?.id ?? null,
      arcadeLoaded,
    }}>
      {children}
    </ArcadeContext.Provider>
  );
}

export function useArcade() {
  return useContext(ArcadeContext);
}
