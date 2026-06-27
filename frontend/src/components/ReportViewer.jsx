export default function ReportViewer({ report }) {
  const latest = report?.latest_version;
  if (!latest) {
    return (
      <div className="panel">
        <h3>No report version yet</h3>
        <p className="small-text">Generate an AI draft report before reviewing the interpretation.</p>
      </div>
    );
  }
  const provider = latest.model_name?.startsWith("remote_medgemma:") ? "remote_medgemma" : latest.model_name;
  return (
    <section className="panel">
      <div className="section-title">
        <h2>AI-assisted report</h2>
        <div className="metadata-line">
          <span>Version {latest.version_number}</span>
          <span>Model: {latest.model_name}</span>
          <span>Provider: {provider}</span>
        </div>
      </div>
      <pre className="report-text">{latest.report_text}</pre>
    </section>
  );
}
