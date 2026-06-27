import { navigate } from "../App.jsx";

export default function Layout({ children }) {
  const path = window.location.pathname;
  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>BioLab Medical AI</h1>
          <p>Biologist Dashboard</p>
        </div>
        <nav>
          <button className={path.startsWith("/cases") || path === "/" ? "active" : ""} onClick={() => navigate("/cases")}>
            Cases
          </button>
          <button className={path.startsWith("/reports") ? "active" : ""} onClick={() => navigate("/reports")}>
            Reports
          </button>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}
