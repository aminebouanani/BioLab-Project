const STATUS_LABELS = {
  READY_FOR_AI: "READY FOR AI",
  AI_DRAFT: "AI DRAFT",
  BIOLOGIST_VALIDATED: "VALIDATED",
  REJECTED: "REJECTED",
  OUTDATED: "OUTDATED",
  PDF_GENERATED: "PDF GENERATED",
  UNKNOWN: "UNKNOWN"
};

export default function StatusBadge({ status }) {
  const normalized = status || "UNKNOWN";
  return <span className={`status-badge status-${normalized}`}>{STATUS_LABELS[normalized] || normalized}</span>;
}
