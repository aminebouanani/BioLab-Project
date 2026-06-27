import { useEffect, useState } from "react";
import { listReports } from "../api/reportsApi.js";
import { navigate } from "../App.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

export default function ReportsPage() {
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadReports() {
    try {
      setLoading(true);
      setError("");
      setReports(await listReports());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReports();
  }, []);

  if (loading) return <LoadingState message="Loading reports..." />;
  if (error) return <ErrorState message={error} onRetry={loadReports} />;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <h2>Reports</h2>
        <p>Open AI drafts, validated reports, rejected reports, and regenerated report versions.</p>
      </section>
      <section className="panel">
        <div className="table-wrap">
          <table className="results-table">
            <thead>
              <tr>
                <th>Report ID</th>
                <th>Patient</th>
                <th>Order</th>
                <th>Specimen</th>
                <th>Status</th>
                <th>Version</th>
                <th>Updated</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {reports.map((report) => (
                <tr key={report.report_id}>
                  <td>{report.report_id}</td>
                  <td>{report.patient_id}</td>
                  <td>{report.order_id}</td>
                  <td>{report.specimen_id}</td>
                  <td><StatusBadge status={report.status} /></td>
                  <td>{report.current_version}</td>
                  <td>{report.updated_at}</td>
                  <td>
                    <button onClick={() => navigate(`/reports/${encodeURIComponent(report.report_id)}`)}>Open Report</button>
                  </td>
                </tr>
              ))}
              {reports.length === 0 && (
                <tr>
                  <td colSpan="8">No reports generated yet. Start from Cases.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}
