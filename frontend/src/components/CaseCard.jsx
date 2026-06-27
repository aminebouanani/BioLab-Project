import { navigate } from "../App.jsx";
import StatusBadge from "./StatusBadge.jsx";

function shortHash(value) {
  if (!value) return "N/A";
  return `${value.slice(0, 10)}...${value.slice(-6)}`;
}

export default function CaseCard({ caseItem }) {
  const openPath = `/cases/${encodeURIComponent(caseItem.patient_id)}/${encodeURIComponent(caseItem.order_id)}?specimen_id=${encodeURIComponent(caseItem.specimen_id)}`;
  return (
    <article className="case-card">
      <div className="card-header">
        <StatusBadge status={caseItem.status} />
        <span className="small-text">{caseItem.results_count} result(s)</span>
      </div>
      <dl>
        <dt>Patient</dt>
        <dd>{caseItem.patient_id}</dd>
        <dt>Order</dt>
        <dd>{caseItem.order_id}</dd>
        <dt>Specimen</dt>
        <dd>{caseItem.specimen_id}</dd>
      </dl>
      <div className="metric-row">
        <span className="metric abnormal">{caseItem.abnormal_results_count} abnormal</span>
        <span className="metric normal">{caseItem.normal_results_count} normal</span>
        <span className="metric unknown">{caseItem.unknown_flag_results_count} unknown</span>
      </div>
      <p className="small-text">Context: {shortHash(caseItem.context_hash)}</p>
      <button onClick={() => navigate(openPath)}>Open Case</button>
    </article>
  );
}
