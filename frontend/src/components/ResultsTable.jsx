function flagClass(flag) {
  if (flag === "H" || flag === "L") return "flag-abnormal";
  if (flag === "N") return "flag-normal";
  return "flag-unknown";
}

export default function ResultsTable({ results = [] }) {
  if (!results.length) {
    return <p className="small-text">No lab results available for this case.</p>;
  }
  return (
    <div className="table-wrap">
      <table className="results-table">
        <thead>
          <tr>
            <th>Test name</th>
            <th>LOINC</th>
            <th>Value</th>
            <th>Unit</th>
            <th>Reference range</th>
            <th>Flag</th>
            <th>Status</th>
            <th>Result datetime</th>
          </tr>
        </thead>
        <tbody>
          {results.map((item, index) => (
            <tr key={item.result_id || `${item.loinc_code}-${index}`}>
              <td>{item.test_name || "Unknown test"}</td>
              <td>{item.loinc_code || item.test_code || "N/A"}</td>
              <td>{item.value_raw ?? item.value_numeric ?? item.value_text ?? ""}</td>
              <td>{item.unit || ""}</td>
              <td>{item.reference_range || "N/A"}</td>
              <td><span className={`flag ${flagClass(item.abnormal_flag)}`}>{item.abnormal_flag || "UNKNOWN"}</span></td>
              <td>{item.validation_status || "UNKNOWN"}</td>
              <td>{String(item.result_datetime || "")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
