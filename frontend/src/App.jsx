import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import Thread from "./pages/Thread";
import Population from "./pages/Population";
import Graph from "./pages/Graph";
import News from "./pages/News";
import { api } from "./api";
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

function SimStatus() {
  const [status, setStatus] = useState(null);
  useEffect(() => {
    const load = () => api.simStatus().then(setStatus).catch(() => {});
    load();
    const id = setInterval(load, 10000);
    return () => clearInterval(id);
  }, []);
  if (!status) return null;
  const running = status.is_running;
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "var(--text)" }}>
      <span>tick {status.current_tick ?? "—"}</span>
      <span style={{ display: "flex", alignItems: "center", gap: 5 }}>
        <span style={{
          width: 6, height: 6,
          background: running ? "#2dd4bf" : "var(--text)",
          display: "inline-block",
          animation: running ? "pulse 2s ease-in-out infinite" : "none",
        }} />
        {running ? "running" : "stopped"}
      </span>
    </span>
  );
}

function Header({ dark, setDark }) {
  const loc = useLocation();
  const inLab = loc.pathname.startsWith("/lab");

  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/social" className="logo-link" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <img src="/favicon.svg" alt="" width={20} height={20} />
          <span className="logo">lurkr</span>
        </NavLink>

        <nav className="nav">
          {/* Social section */}
          <NavLink to="/social" className={() => `section-tab${loc.pathname.startsWith("/social") ? " section-active" : ""}`}>
            Social
          </NavLink>
          <NavLink to="/social" end className="subnav-link">Timeline</NavLink>
          <NavLink to="/social/agents" className="subnav-link">Robots</NavLink>

          {/* Divider */}
          <span className="nav-divider" />

          {/* Lab section */}
          <NavLink to="/lab" className={`section-tab${inLab ? " section-active" : ""}`}>
            Lab
          </NavLink>
          <NavLink to="/lab" end className="subnav-link">Drift</NavLink>
          <NavLink to="/lab/network" className="subnav-link">Network</NavLink>
          <NavLink to="/lab/news" className="subnav-link">News</NavLink>

          {inLab && (
            <>
              <span className="nav-divider" />
              <SimStatus />
            </>
          )}
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
  );
}

export default function App() {
  const [dark, setDark] = useDarkMode();

  return (
    <BrowserRouter>
      <div className="app">
        <Header dark={dark} setDark={setDark} />
        <main className="main">
          <Routes>
            <Route path="/"                      element={<Navigate to="/social" replace />} />
            <Route path="/social"                element={<Timeline />} />
            <Route path="/social/agents"         element={<Agents />} />
            <Route path="/social/agents/:id"     element={<AgentProfile />} />
            <Route path="/social/thread/:id"     element={<Thread />} />
            <Route path="/lab"                   element={<Population />} />
            <Route path="/lab/network"           element={<Graph />} />
            <Route path="/lab/news"              element={<News />} />
            {/* Legacy redirects */}
            <Route path="/agents"                element={<Navigate to="/social/agents" replace />} />
            <Route path="/population"            element={<Navigate to="/lab" replace />} />
            <Route path="/graph"                 element={<Navigate to="/lab/network" replace />} />
            <Route path="/news"                  element={<Navigate to="/lab/news" replace />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
