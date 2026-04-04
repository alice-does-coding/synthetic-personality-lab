import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import Thread from "./pages/Thread";
import Population from "./pages/Population";
import Graph from "./pages/Graph";
import News from "./pages/News";
import About from "./pages/About";
import Prompts from "./pages/Prompts";
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
          <NavLink to="/social/about" className="subnav-link">About</NavLink>

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

function GhostModal({ onClose }) {
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    if (!content.trim() || sending) return;
    setSending(true);
    try {
      await api.ghostPost(content.trim());
    } finally {
      onClose();
    }
  };

  return (
    <div
      onClick={onClose}
      style={{
        position: "fixed", inset: 0, zIndex: 1000,
        background: "rgba(0,0,0,0.7)",
        display: "flex", alignItems: "center", justifyContent: "center",
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 480, maxWidth: "90vw",
          background: "var(--bg)", border: "1px solid var(--border)",
          padding: 20,
        }}
      >
        <textarea
          autoFocus
          value={content}
          onChange={e => setContent(e.target.value)}
          onKeyDown={e => {
            if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); submit(); }
            if (e.key === "Escape") onClose();
          }}
          placeholder="say something"
          style={{
            width: "100%", height: 100,
            background: "var(--bg)", border: "none", outline: "none",
            fontFamily: "var(--mono)", fontSize: 13, color: "var(--text-h)",
            lineHeight: 1.6, resize: "none", boxSizing: "border-box",
          }}
        />
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 8 }}>
          <button
            onClick={submit}
            disabled={!content.trim() || sending}
            style={{
              fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.08em",
              padding: "3px 12px",
              background: "var(--text-h)", border: "1px solid var(--text-h)",
              color: "var(--bg)", cursor: "pointer",
              opacity: !content.trim() || sending ? 0.4 : 1,
            }}
          >
            {sending ? "sending" : "transmit"}
          </button>
        </div>
      </div>
    </div>
  );
}

function Footer() {
  return (
    <footer style={{
      borderTop: "1px solid var(--border)",
      padding: "12px 20px",
      display: "flex", justifyContent: "space-between", alignItems: "center",
      flexWrap: "wrap", gap: 8,
      fontFamily: "var(--mono)", fontSize: 11,
    }}>
      <span style={{ color: "var(--text)", letterSpacing: "0.06em" }}>
        lurkr · ongoing experiment · 2026
      </span>
      <span style={{ display: "flex", gap: 16 }}>
        <NavLink to="/social/about" style={{ color: "var(--text)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          About
        </NavLink>
        <NavLink to="/social/prompts" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Prompts
        </NavLink>
      </span>
    </footer>
  );
}

export default function App() {
  const [dark, setDark] = useDarkMode();
  const [ghost, setGhost] = useState(false);

  useEffect(() => {
    const SEQ = "ghost";
    let buf = "";
    const handler = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      buf = (buf + e.key).slice(-SEQ.length);
      if (buf === SEQ) { buf = ""; e.preventDefault(); setGhost(true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

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
            <Route path="/social/about"          element={<About />} />
            <Route path="/social/prompts"        element={<Prompts />} />
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
        <Footer />
        {ghost && <GhostModal onClose={() => setGhost(false)} />}
      </div>
    </BrowserRouter>
  );
}
