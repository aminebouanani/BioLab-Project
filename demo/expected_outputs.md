# Expected Outputs

## Service Health Checker

Example:

```text
Service          | URL/Check                         | Status | Details
-----------------+-----------------------------------+--------+-------------------------------
Fake GLIMS API   | http://127.0.0.1:8000/health      | OK     | service_name=fake-glims-api
AI Backend       | http://127.0.0.1:8001/health      | OK     | active_provider=remote_medgemma
React Dashboard  | http://localhost:5173             | OK     | HTTP 200
Remote MedGemma  | <MEDGEMMA_API_URL>/health         | OK     | provider=remote_medgemma
Redpanda/Kafka   | docker ps or Kafka topic metadata | OK     | Topics present
```

## Pre-Azure Validation PASS

```text
PRE-AZURE VALIDATION PASSED
Report ID: RPT-...
Provider used: remote_medgemma
Model name: medgemma-4b-it
PDF: final_pdf_RPT-..._v1.pdf
```

## AI Backend Health

```json
{
  "configured_ai_provider": "remote_medgemma",
  "active_provider": "remote_medgemma",
  "require_real_llm": true,
  "is_real_llm": true,
  "model_name": "medgemma-4b-it",
  "provider_ready": true
}
```

## Report Generation Response

```json
{
  "report_id": "RPT-...",
  "version_number": 1,
  "status": "AI_DRAFT",
  "model_name": "medgemma-4b-it",
  "provider_used": "remote_medgemma",
  "is_real_llm": true,
  "report_text": "AI Draft Biological Report..."
}
```

## Chat Response

```json
{
  "report_id": "RPT-...",
  "provider_used": "remote_medgemma",
  "is_real_llm": true,
  "answer": "The abnormal findings include..."
}
```

## PDF Export Response

```json
{
  "export_id": "EXP-...",
  "report_id": "RPT-...",
  "pdf_filename": "final_pdf_RPT-..._v1.pdf",
  "export_status": "GENERATED",
  "export_type": "FINAL_PDF",
  "download_url": "/reports/RPT-.../pdf/download"
}
```

## Validation Summary JSON

```json
{
  "result": "PASS",
  "selected_patient_id": "PAT-...",
  "order_id": "ORD-...",
  "specimen_id": "SPC-...",
  "report_id": "RPT-...",
  "model_name": "medgemma-4b-it",
  "provider_used": "remote_medgemma",
  "is_real_llm": true,
  "pdf_export_id": "EXP-...",
  "pdf_filename": "final_pdf_RPT-..._v1.pdf",
  "steps": [
    {"step": "AI backend health", "status": "PASS"},
    {"step": "AI report generated", "status": "PASS"},
    {"step": "Chatbot answered", "status": "PASS"},
    {"step": "Report validated", "status": "PASS"},
    {"step": "Final PDF generated", "status": "PASS"},
    {"step": "PDF downloaded", "status": "PASS"}
  ]
}
```
