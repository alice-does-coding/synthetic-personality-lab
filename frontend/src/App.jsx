import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import SimControls from "./components/SimControls";
import "./App.css";

export default function App() {
  return (
    <BrowserRouter>
      <div className="app">
        <header className="header">
          <div className="header-inner">
            <span className="logo">lurkr</span>
            <nav className="nav">
              <NavLink to="/" end>Timeline</NavLink>
              <NavLink to="/agents">Agents</NavLink>
            </nav>
            <SimControls />
          </div>
        </header>
        <main className="main">
          <Routes>
            <Route path="/"           element={<Timeline />} />
            <Route path="/agents"     element={<Agents />} />
            <Route path="/agents/:id" element={<AgentProfile />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
