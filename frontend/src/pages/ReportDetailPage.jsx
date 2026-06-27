import { useEffect, useState } from "react";
import { getReport } from "../api/reportsApi.js";
import ChatPanel from "../components/ChatPanel.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import PdfPanel from "../components/PdfPanel.jsx";
import ReportActions from "../components/ReportActions.jsx";
import ReportViewer from "../components/ReportViewer.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

export default function ReportDetailPage({ reportId }) {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadReport() {
    try {
      setLoading(true);
      setError("");
      setReport(await getReport(reportId));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadReport();
  }, [reportId]);

  if (loading) return <LoadingState message="Loading report..." />;
  if (error) return <ErrorState message={error} onRetry={loadReport} />;
  if (!report) return <ErrorState message="Report not found." />;

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>{report.report_id}</h2>
            <p className="small-text">Current version {report.current_version}</p>
          </div>
          <StatusBadge status={report.status} />
        </div>
        <dl className="metadata-grid">
          <dt>Patient ID</dt>
          <dd>{report.patient_id}</dd>
          <dt>Order ID</dt>
          <dd>{report.order_id}</dd>
          <dt>Specimen ID</dt>
          <dd>{report.specimen_id}</dd>
          <dt>Created</dt>
          <dd>{report.created_at}</dd>
          <dt>Updated</dt>
          <dd>{report.updated_at}</dd>
        </dl>
      </section>
      <ReportViewer report={report} />
      <div className="two-column">
        <ReportActions report={report} onChanged={loadReport} />
        <PdfPanel report={report} />
      </div>
      <ChatPanel report={report} />
    </div>
  );
}
