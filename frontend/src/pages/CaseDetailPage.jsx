import { useEffect, useMemo, useState } from "react";
import { getCase } from "../api/casesApi.js";
import { generateReport, listReports } from "../api/reportsApi.js";
import { navigate } from "../App.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";
import ResultsTable from "../components/ResultsTable.jsx";
import StatusBadge from "../components/StatusBadge.jsx";

function shortHash(value) {
  if (!value) return "N/A";
  return `${value.slice(0, 16)}...${value.slice(-8)}`;
}

export default function CaseDetailPage({ patientId, orderId, specimenId }) {
  const [caseItem, setCaseItem] = useState(null);
  const [reports, setReports] = useState([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState("");

  async function loadData() {
    try {
      setLoading(true);
      setError("");
      const [caseData, reportData] = await Promise.all([
        getCase(patientId, orderId, specimenId),
        listReports().catch(() => [])
      ]);
      setCaseItem(caseData);
      setReports(reportData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [patientId, orderId, specimenId]);

  const existingReport = useMemo(() => {
    if (!caseItem) return null;
    return reports.find(
      (report) =>
        report.patient_id === caseItem.patient_id &&
        report.order_id === caseItem.order_id &&
        report.specimen_id === caseItem.specimen_id
    );
  }, [reports, caseItem]);

  async function handleGenerate() {
    try {
      setGenerating(true);
      setError("");
      const report = await generateReport({
        patient_id: caseItem.patient_id,
        order_id: caseItem.order_id,
        specimen_id: caseItem.specimen_id
      });
      navigate(`/reports/${encodeURIComponent(report.report_id)}`);
    } catch (err) {
      setError(err.message);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) return <LoadingState message="Loading case details..." />;
  if (error) return <ErrorState message={error} onRetry={loadData} />;
  if (!caseItem) return <ErrorState message="Case not found." />;

  return (
    <div className="page-stack">
      <section className="panel">
        <div className="section-title">
          <div>
            <h2>Case detail</h2>
            <p className="small-text">Patient/order/specimen report context from Gold.</p>
          </div>
          <StatusBadge status={caseItem.status} />
        </div>
        <dl className="metadata-grid">
          <dt>Patient ID</dt>
          <dd>{caseItem.patient_id}</dd>
          <dt>Order ID</dt>
          <dd>{caseItem.order_id}</dd>
          <dt>Specimen ID</dt>
          <dd>{caseItem.specimen_id}</dd>
          <dt>Context hash</dt>
          <dd>{shortHash(caseItem.context_hash)}</dd>
          <dt>Result window</dt>
          <dd>{caseItem.first_result_datetime} to {caseItem.last_result_datetime}</dd>
        </dl>
        <div className="metric-row">
          <span className="metric abnormal">{caseItem.abnormal_results_count} abnormal</span>
          <span className="metric normal">{caseItem.normal_results_count} normal</span>
          <span className="metric unknown">{caseItem.unknown_flag_results_count} unknown</span>
          <span className="metric">{caseItem.results_count} total</span>
        </div>
        <div className="button-row">
          <button onClick={handleGenerate} disabled={generating}>
            {generating ? "Generating..." : "Generate AI Report"}
          </button>
          {existingReport && (
            <button className="secondary" onClick={() => navigate(`/reports/${encodeURIComponent(existingReport.report_id)}`)}>
              Open Existing Report
            </button>
          )}
        </div>
        {existingReport && (
          <p className="small-text">Existing report found: {existingReport.report_id} ({existingReport.status})</p>
        )}
      </section>
      <section className="panel">
        <h2>Lab results</h2>
        <ResultsTable results={caseItem.results} />
      </section>
    </div>
  );
}
