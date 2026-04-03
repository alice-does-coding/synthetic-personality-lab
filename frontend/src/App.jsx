import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import Timeline from "./pages/Timeline";
import Agents from "./pages/Agents";
import AgentProfile from "./pages/AgentProfile";
import Thread from "./pages/Thread";
import Population from "./pages/Population";
import News from "./pages/News";
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
              <NavLink to="/population">Population</NavLink>
              <NavLink to="/news">News</NavLink>
            </nav>
          </div>
        </header>
        <main className="main">
          <Routes>
            <Route path="/"           element={<Timeline />} />
            <Route path="/agents"     element={<Agents />} />
            <Route path="/agents/:id" element={<AgentProfile />} />
            <Route path="/thread/:id"  element={<Thread />} />
            <Route path="/population" element={<Population />} />
            <Route path="/news"       element={<News />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}
