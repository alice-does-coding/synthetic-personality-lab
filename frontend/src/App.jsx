import { BrowserRouter, Routes, Route, NavLink, Navigate, useLocation } from "react-router-dom";
import { useState, useEffect } from "react";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import Thread from "./pages/Thread";
import Population from "./pages/Population";
import Graph from "./pages/Graph";
import News from "./pages/News";
import Runs from "./pages/Runs";
import About from "./pages/About";
import Prompts from "./pages/Prompts";
import CreateAgent from "./pages/CreateAgent";
import { api } from "./api";
import { RunProvider, useRun } from "./RunContext";
import { AdminProvider, useAdmin } from "./AdminContext";
import { SimulationProvider } from "./SimulationContext";
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
  const { viewingRun, runningRunIds } = useRun();
  if (!viewingRun) return null;
  const isRunning = runningRunIds.includes(viewingRun.id);
  return (
    <span style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 11, color: "var(--text)", fontFamily: "var(--mono)", minWidth: 0 }}>
      <span style={{ whiteSpace: "nowrap", flexShrink: 0, color: "var(--text-h)", fontWeight: 700 }}>
        t{viewingRun.last_tick ?? "—"}
        <span style={{
          display: "inline-block",
          width: 6, height: 6,
          marginLeft: 6,
          background: isRunning ? "#2dd4bf" : "var(--text)",
          animation: isRunning ? "pulse 2s ease-in-out infinite" : "none",
          verticalAlign: "middle",
        }} />
      </span>
    </span>
  );
}


function Header({ dark, setDark, onAdminClick, isAdmin }) {
  const loc = useLocation();
  const inLab = loc.pathname.startsWith("/lab");

  return (
    <header className="header">
      <div className="header-inner">
        <NavLink to="/social" className="logo-link" style={{ textDecoration: "none", display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          <img src="/favicon.svg" alt="" width={20} height={20} />
          <span className="logo">Synthetic Personality Lab</span>
        </NavLink>

        <nav className="nav">
          {/* Social section */}
          <NavLink to="/social" className={() => `section-tab${loc.pathname.startsWith("/social") ? " section-active" : ""}`}>
            Social
          </NavLink>
          <NavLink to="/social" end className="subnav-link">Timeline</NavLink>
          <NavLink to="/social/agents" className="subnav-link">Agents</NavLink>

          {/* Divider */}
          <span className="nav-divider" />

          {/* Lab section */}
          <NavLink to="/lab" className={`section-tab${inLab ? " section-active" : ""}`}>
            Lab
          </NavLink>
          <NavLink to="/lab" end className="subnav-link">Population</NavLink>
          <NavLink to="/lab/network" className="subnav-link">Network</NavLink>
          <NavLink to="/lab/news" className="subnav-link">News</NavLink>
          {isAdmin && <NavLink to="/lab/runs" className="subnav-link">Runs</NavLink>}
          <NavLink to="/lab/about" className="subnav-link">About</NavLink>

          <span className="nav-divider" />
          <SimStatus />
        </nav>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexShrink: 0 }}>
          {isAdmin && (
            <button
              onClick={onAdminClick}
              style={{
                fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
                textTransform: "uppercase", letterSpacing: "0.08em",
                padding: "3px 10px", cursor: "pointer",
                border: "1px solid #2dd4bf",
                background: "var(--bg)", color: "#2dd4bf",
              }}
            >
              admin
            </button>
          )}
          <button
            onClick={() => setDark(d => !d)}
            style={{
              fontFamily: "var(--mono)", fontSize: 11, fontWeight: 700,
              textTransform: "uppercase", letterSpacing: "0.08em",
              padding: "3px 10px",
              border: "1px solid var(--border)",
              background: "var(--bg)", color: "var(--text)",
              cursor: "pointer",
            }}
          >
            {dark ? "light" : "dark"}
          </button>
        </div>
      </div>
    </header>
  );
}


function AdminModal({ onClose }) {
  const { isAdmin, unlock, lock } = useAdmin();
  const [key, setKey] = useState("");
  const [error, setError] = useState(null);

  const submit = async () => {
    if (!key.trim()) return;
    // Smoke-test the key before storing
    try {
      await api.simStatus(); // public endpoint just to confirm network is up
      unlock(key.trim());
      onClose();
    } catch {
      setError("could not verify — key stored anyway");
      unlock(key.trim());
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
          width: 380, maxWidth: "90vw",
          background: "var(--bg)", border: "1px solid var(--text-h)",
          padding: 24, display: "flex", flexDirection: "column", gap: 16,
          fontFamily: "var(--mono)",
        }}
      >
        <div style={{ fontSize: 10, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.15em", color: "var(--text-h)" }}>
          admin
        </div>

        {isAdmin ? (
          <>
            <div style={{ fontSize: 12, color: "var(--text)" }}>
              <span style={{ color: "#2dd4bf", fontWeight: 700 }}>●</span> admin mode active
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={() => { lock(); onClose(); }}
                style={{
                  fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
                  textTransform: "uppercase", letterSpacing: "0.08em",
                  padding: "5px 16px", cursor: "pointer",
                  border: "1px solid #fb7185", background: "var(--bg)", color: "#fb7185",
                }}
              >
                lock
              </button>
              <button
                onClick={onClose}
                style={{
                  fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
                  textTransform: "uppercase", letterSpacing: "0.08em",
                  padding: "5px 16px", cursor: "pointer",
                  border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)",
                }}
              >
                close
              </button>
            </div>
          </>
        ) : (
          <>
            <input
              autoFocus
              type="password"
              value={key}
              onChange={e => setKey(e.target.value)}
              onKeyDown={e => {
                if (e.key === "Enter") submit();
                if (e.key === "Escape") onClose();
              }}
              placeholder="admin key"
              style={{
                fontFamily: "var(--mono)", fontSize: 13,
                background: "var(--bg)", color: "var(--text-h)",
                border: "1px solid var(--border)",
                padding: "7px 10px", outline: "none", width: "100%", boxSizing: "border-box",
              }}
            />
            {error && <span style={{ fontSize: 10, color: "#fb7185" }}>{error}</span>}
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={submit}
                disabled={!key.trim()}
                style={{
                  fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
                  textTransform: "uppercase", letterSpacing: "0.08em",
                  padding: "5px 16px", cursor: "pointer",
                  border: "1px solid var(--text-h)", background: "var(--text-h)", color: "var(--bg)",
                  opacity: !key.trim() ? 0.4 : 1,
                }}
              >
                unlock
              </button>
              <button
                onClick={onClose}
                style={{
                  fontFamily: "var(--mono)", fontSize: 10, fontWeight: 700,
                  textTransform: "uppercase", letterSpacing: "0.08em",
                  padding: "5px 16px", cursor: "pointer",
                  border: "1px solid var(--border)", background: "var(--bg)", color: "var(--text)",
                }}
              >
                cancel
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function GhostModal({ onClose }) {
  const { viewingRunId } = useRun();
  const [content, setContent] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    if (!content.trim() || sending || !viewingRunId) return;
    setSending(true);
    try {
      await api.ghostPost(viewingRunId, content.trim());
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
        Synthetic Personality Lab · ongoing experiment · 2026
        <NavLink
          to="/create"
          style={{
            marginLeft: 16,
            color: "var(--text)",
            textDecoration: "none",
            opacity: 0.25,
            transition: "opacity 0.3s",
            letterSpacing: "0.06em",
          }}
          onMouseEnter={e => e.currentTarget.style.opacity = 0.7}
          onMouseLeave={e => e.currentTarget.style.opacity = 0.25}
        >
          join
        </NavLink>
      </span>
      <span style={{ display: "flex", gap: 16 }}>
        <NavLink to="/lab/about" style={{ color: "var(--text)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          About
        </NavLink>
        <NavLink to="/social/prompts" target="_blank" rel="noopener noreferrer" style={{ color: "var(--text)", textDecoration: "none", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Prompts
        </NavLink>
      </span>
    </footer>
  );
}

function AppInner({ dark, setDark }) {
  const [ghost, setGhost] = useState(false);
  const [admin, setAdmin] = useState(false);
  const { isAdmin } = useAdmin();

  useEffect(() => {
    const SEQS = ["ghost", "admin"];
    const maxLen = Math.max(...SEQS.map(s => s.length));
    let buf = "";
    const handler = (e) => {
      if (e.target.tagName === "INPUT" || e.target.tagName === "TEXTAREA") return;
      buf = (buf + e.key).slice(-maxLen);
      if (buf.endsWith("ghost")) { buf = ""; setGhost(true); }
      if (buf.endsWith("admin")) { buf = ""; setAdmin(true); }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  return (
    <div className="app">
      <Header dark={dark} setDark={setDark} onAdminClick={() => setAdmin(true)} isAdmin={isAdmin} />
      <main className="main">
        <Routes>
          <Route path="/"                      element={<Navigate to="/social" replace />} />
          <Route path="/social"                element={<Timeline />} />
          <Route path="/social/agents"         element={<Agents />} />
          <Route path="/create"                element={<CreateAgent />} />
          <Route path="/join"                  element={<Navigate to="/create" replace />} />
          <Route path="/social/create"         element={<Navigate to="/create" replace />} />
          <Route path="/social/agents/:id"     element={<AgentProfile />} />
          <Route path="/social/thread/:id"     element={<Thread />} />
          <Route path="/lab/about"             element={<About />} />
          <Route path="/social/prompts"        element={<Prompts />} />
          {/* Legacy redirect */}
          <Route path="/social/about"          element={<Navigate to="/lab/about" replace />} />
          <Route path="/lab"                   element={<Population />} />
          <Route path="/lab/network"           element={<Graph />} />
          <Route path="/lab/news"              element={<News />} />
          <Route path="/lab/runs"              element={isAdmin ? <Runs /> : <Navigate to="/lab" replace />} />
          {/* Legacy redirects */}
          <Route path="/agents"                element={<Navigate to="/social/agents" replace />} />
          <Route path="/population"            element={<Navigate to="/lab" replace />} />
          <Route path="/graph"                 element={<Navigate to="/lab/network" replace />} />
          <Route path="/news"                  element={<Navigate to="/lab/news" replace />} />
        </Routes>
      </main>
      <Footer />
      {ghost && <GhostModal onClose={() => setGhost(false)} />}
      {admin && <AdminModal onClose={() => setAdmin(false)} />}
    </div>
  );
}

export default function App() {
  const [dark, setDark] = useDarkMode();
  return (
    <BrowserRouter>
      <AdminProvider>
        <RunProvider>
          <SimulationProvider>
            <AppInner dark={dark} setDark={setDark} />
          </SimulationProvider>
        </RunProvider>
      </AdminProvider>
    </BrowserRouter>
  );
}
