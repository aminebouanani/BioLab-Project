import { useEffect, useMemo, useState } from "react";
import Layout from "./components/Layout.jsx";
import CasesPage from "./pages/CasesPage.jsx";
import CaseDetailPage from "./pages/CaseDetailPage.jsx";
import ReportsPage from "./pages/ReportsPage.jsx";
import ReportDetailPage from "./pages/ReportDetailPage.jsx";

function currentRoute() {
  const url = new URL(window.location.href);
  return {
    path: url.pathname,
    searchParams: url.searchParams
  };
}

export function navigate(path) {
  window.history.pushState({}, "", path);
  window.dispatchEvent(new Event("biolab:navigate"));
}

function parseRoute(path) {
  const parts = path.split("/").filter(Boolean);
  if (parts.length === 0) {
    return { page: "cases" };
  }
  if (parts[0] === "cases" && parts.length === 1) {
    return { page: "cases" };
  }
  if (parts[0] === "cases" && parts.length >= 3) {
    return {
      page: "case-detail",
      patientId: decodeURIComponent(parts[1]),
      orderId: decodeURIComponent(parts[2])
    };
  }
  if (parts[0] === "reports" && parts.length === 1) {
    return { page: "reports" };
  }
  if (parts[0] === "reports" && parts.length >= 2) {
    return { page: "report-detail", reportId: decodeURIComponent(parts[1]) };
  }
  return { page: "not-found" };
}

export default function App() {
  const [route, setRoute] = useState(currentRoute());

  useEffect(() => {
    const sync = () => setRoute(currentRoute());
    window.addEventListener("popstate", sync);
    window.addEventListener("biolab:navigate", sync);
    return () => {
      window.removeEventListener("popstate", sync);
      window.removeEventListener("biolab:navigate", sync);
    };
  }, []);

  const parsed = useMemo(() => parseRoute(route.path), [route.path]);

  let page;
  if (parsed.page === "cases") {
    page = <CasesPage />;
  } else if (parsed.page === "case-detail") {
    page = (
      <CaseDetailPage
        patientId={parsed.patientId}
        orderId={parsed.orderId}
        specimenId={route.searchParams.get("specimen_id")}
      />
    );
  } else if (parsed.page === "reports") {
    page = <ReportsPage />;
  } else if (parsed.page === "report-detail") {
    page = <ReportDetailPage reportId={parsed.reportId} />;
  } else {
    page = (
      <div className="panel">
        <h2>Page not found</h2>
        <p>The requested dashboard page does not exist.</p>
      </div>
    );
  }

  return <Layout>{page}</Layout>;
}
