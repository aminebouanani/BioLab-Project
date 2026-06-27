import { useEffect, useMemo, useState } from "react";
import { listCases } from "../api/casesApi.js";
import CaseCard from "../components/CaseCard.jsx";
import ErrorState from "../components/ErrorState.jsx";
import LoadingState from "../components/LoadingState.jsx";

export default function CasesPage() {
  const [cases, setCases] = useState([]);
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  async function loadCases() {
    try {
      setLoading(true);
      setError("");
      setCases(await listCases());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadCases();
  }, []);

  const filtered = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) return cases;
    return cases.filter((item) =>
      [item.patient_id, item.order_id, item.specimen_id, item.status]
        .join(" ")
        .toLowerCase()
        .includes(term)
    );
  }, [cases, query]);

  if (loading) return <LoadingState message="Loading Gold report-ready cases..." />;
  if (error) return <ErrorState message={error} onRetry={loadCases} />;

  return (
    <div className="page-stack">
      <section className="hero-panel">
        <h2>Gold report-ready cases</h2>
        <p>
          Review patient/order/specimen contexts from the local Gold layer and generate AI-assisted draft reports.
        </p>
      </section>
      <section className="toolbar">
        <div>
          <strong>{filtered.length}</strong> of {cases.length} case(s)
        </div>
        <input
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search patient, order, specimen, status..."
        />
      </section>
      <div className="case-grid">
        {filtered.map((caseItem) => (
          <CaseCard key={`${caseItem.patient_id}-${caseItem.order_id}-${caseItem.specimen_id}`} caseItem={caseItem} />
        ))}
      </div>
    </div>
  );
}
