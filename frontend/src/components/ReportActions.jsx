import { useState } from "react";
import { checkOutdated, regenerateReport, rejectReport, validateReport } from "../api/reportsApi.js";
import ErrorState from "./ErrorState.jsx";

export default function ReportActions({ report, onChanged }) {
  const [comment, setComment] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const status = report?.status;
  const validateDisabled = status === "OUTDATED" || status === "REJECTED" || status === "BIOLOGIST_VALIDATED";
  const rejectDisabled = status === "BIOLOGIST_VALIDATED" || status === "OUTDATED" || status === "REJECTED";
  const regenerateDisabled = busy;

  async function runAction(action) {
    try {
      setBusy(true);
      setError("");
      setMessage("");
      const result = await action();
      setMessage("Action completed successfully.");
      setComment("");
      await onChanged?.(result);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h2>Report actions</h2>
      {error && <ErrorState message={error} />}
      {message && <p className="success-message">{message}</p>}
      <label className="field">
        Optional biologist comment
        <textarea value={comment} onChange={(event) => setComment(event.target.value)} placeholder="Add validation or rejection note..." />
      </label>
      <div className="button-row">
        <button disabled={busy} onClick={() => runAction(() => checkOutdated(report.report_id))}>
          Check outdated
        </button>
        <button disabled={regenerateDisabled} onClick={() => runAction(() => regenerateReport(report.report_id))}>
          Regenerate
        </button>
        <button disabled={busy || validateDisabled} onClick={() => runAction(() => validateReport(report.report_id, comment))}>
          Validate
        </button>
        <button className="danger" disabled={busy || rejectDisabled} onClick={() => runAction(() => rejectReport(report.report_id, comment))}>
          Reject
        </button>
      </div>
      <p className="small-text">
        Validation is blocked for OUTDATED or REJECTED reports. Final PDF export is unlocked only after validation.
      </p>
    </section>
  );
}
