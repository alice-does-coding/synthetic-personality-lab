import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { useState, useEffect } from "react";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import Thread from "./pages/Thread";
import Population from "./pages/Population";
import Graph from "./pages/Graph";
import News from "./pages/News";
import "./App.css";

function useDarkMode() {
  const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
  const [dark, setDark] = useState(() => {
    const stored = localStorage.getItem("theme");
    return stored ? stored === "dark" : prefersDark;
  });

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", dark ? "dark" : "light");
    localStorage.setItem("theme", dark ? "dark" : "light");
  }, [dark]);

  return [dark, setDark];
}

export default function App() {
  const [dark, setDark] = useDarkMode();

  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="header-inner">
            <NavLink to="/" end className="logo-link" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
              <img src="/favicon.svg" alt="" width={20} height={20} />
              <span className="logo">lurkr</span>
            </NavLink>
            <nav className="nav">
              <NavLink to="/" end>Timeline</NavLink>
              <NavLink to="/agents">Agents</NavLink>
              <NavLink to="/population">Population</NavLink>
              <NavLink to="/graph">Graph</NavLink>
              <NavLink to="/news">News</NavLink>
            </nav>
            <button
              onClick={() => setDark(d => !d)}
              style={{
                fontFamily: "var(--mono)",
                fontSize: 11, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.08em",
                padding: "3px 10px",
                border: "1px solid var(--border)",
                background: "var(--bg)", color: "var(--text)",
                cursor: "pointer", flexShrink: 0,
              }}
            >
              {dark ? "light" : "dark"}
            </button>
          </div>
        </header>
        <main className="main">
          <Routes>
            <Route path="/"           element={<Timeline />} />
            <Route path="/agents"     element={<Agents />} />
            <Route path="/agents/:id" element={<AgentProfile />} />
            <Route path="/thread/:id"  element={<Thread />} />
            <Route path="/population" element={<Population />} />
            <Route path="/graph"      element={<Graph />} />
            <Route path="/news"       element={<News />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
