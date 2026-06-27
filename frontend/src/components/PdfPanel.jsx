import { useEffect, useState } from "react";
import { generateFinalPdf, getLatestPdf, pdfDownloadUrl } from "../api/pdfApi.js";
import ErrorState from "./ErrorState.jsx";
import StatusBadge from "./StatusBadge.jsx";

export default function PdfPanel({ report }) {
  const [pdf, setPdf] = useState(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  const canGenerate = report?.status === "BIOLOGIST_VALIDATED";
  const blockedReason = report?.status === "BIOLOGIST_VALIDATED"
    ? ""
    : "Official PDF generation requires BIOLOGIST_VALIDATED status.";

  async function loadPdf() {
    if (!report?.report_id) return;
    try {
      setError("");
      setPdf(await getLatestPdf(report.report_id));
    } catch (err) {
      setPdf(null);
      if (!err.message.includes("No PDF export exists")) {
        setError(err.message);
      }
    }
  }

  useEffect(() => {
    loadPdf();
  }, [report?.report_id]);

  async function generatePdf() {
    try {
      setBusy(true);
      setError("");
      setMessage("");
      const exportMeta = await generateFinalPdf(report.report_id);
      setPdf(exportMeta);
      setMessage("Final PDF generated successfully.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <div className="section-title">
        <h2>PDF export</h2>
        {pdf && <StatusBadge status="PDF_GENERATED" />}
      </div>
      {error && <ErrorState message={error} onRetry={loadPdf} />}
      {message && <p className="success-message">{message}</p>}
      {pdf ? (
        <dl className="metadata-grid">
          <dt>Export ID</dt>
          <dd>{pdf.export_id}</dd>
          <dt>Type</dt>
          <dd>{pdf.export_type}</dd>
          <dt>Filename</dt>
          <dd>{pdf.pdf_filename}</dd>
          <dt>Generated at</dt>
          <dd>{pdf.generated_at}</dd>
          <dt>Size</dt>
          <dd>{pdf.file_size_bytes || 0} bytes</dd>
        </dl>
      ) : (
        <p className="small-text">No PDF has been generated for this report yet.</p>
      )}
      {!canGenerate && <p className="lock-message">{blockedReason}</p>}
      <div className="button-row">
        <button disabled={!canGenerate || busy} onClick={generatePdf}>
          {busy ? "Generating..." : "Generate Final PDF"}
        </button>
        <a
          className={`button-link ${pdf ? "" : "disabled"}`}
          href={pdf ? pdfDownloadUrl(report.report_id) : "#"}
          target="_blank"
          rel="noreferrer"
          onClick={(event) => {
            if (!pdf) event.preventDefault();
          }}
        >
          Download PDF
        </a>
      </div>
    </section>
  );
}
