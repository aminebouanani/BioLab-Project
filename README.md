# BioLab Project

Cloud-native post-analytical biological reporting project. This first component
adapts local Synthea laboratory data into pseudonymized, fake GLIMS-like
`LAB_RESULT_CREATED` events. Local Kafka-compatible streaming is available with
Redpanda. The project does not yet include Spark, Azure, AI, or a frontend.

## What the adapter does

1. Extracts every ZIP from `data/raw/synthea_zips/` into
   `data/extracted/synthea/`.
2. Detects available Synthea CSV and FHIR JSON data.
3. Prefers CSV when `patients.csv` and `observations.csv` exist together.
4. Keeps laboratory observations and maps them to GLIMS-like events.
5. Pseudonymizes source patient IDs with HMAC-SHA256.
6. Writes newline-delimited JSON to
   `data/bronze/glims_lab_results.jsonl`.

The bronze output never contains patient names, addresses, phone numbers, birth
dates, or source patient identifiers.

## Setup

Python 3.8 or newer is recommended.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Replace `GLIMS_HMAC_SECRET` in `.env` with a private random value containing at
least 32 characters. Keep the same secret between runs when stable patient
pseudonyms are required.

Place Synthea ZIP archives in:

```text
data/raw/synthea_zips/
```

Paths can be overridden in `.env`. This is useful when ZIP archives are stored
outside the repository:

```dotenv
SYNTHEA_ZIP_DIR=C:\path\to\synthea_zips
```

If the configured directory is missing, the adapter also checks common sibling
`data/raw/synthea_zips/` and legacy `data/raw/sythea_zips/` layouts.

## Run

From the repository root:

```powershell
python -m glims_adapter.main
```

The adapter logs whether CSV or FHIR was selected and how many events were
written. CSV is preferred whenever a matching `patients.csv` and
`observations.csv` pair is found.

## Event shape

Each output line is a validated JSON object containing:

```text
event_id, source_system, origin_source, event_type, patient_id, order_id,
specimen_id, test_code, loinc_code, test_name, value, unit, reference_range,
abnormal_flag, validation_status, result_datetime
```

`source_system` is `GLIMS_SIM`, `event_type` is `LAB_RESULT_CREATED`, and
`origin_source` remains `SYNTHEA` to preserve source lineage.

The internal normalized schema isolates source readers from the public event
schema, making the mapper ready for later Kafka or Azure Event Hubs publishing
without changing ingestion logic.

## Sample Data

Full generated health-style data remains local and is not pushed to GitHub. A
small sample of 100 fake GLIMS-like events is included in
`samples/glims_lab_results_sample.jsonl` only to show the event schema.

Regenerate the full local dataset with:

```powershell
python -m glims_adapter.main
```

Regenerate the committable sample with:

```powershell
python scripts/create_sample_dataset.py
```

## Fake GLIMS API

The Fake GLIMS API simulates the source/integration layer of a real GLIMS/LIS.
It reads fake GLIMS-like lab-result events from the local bronze JSONL file and
exposes patients, orders, results, modified results, and simulated updates over
HTTP. This layer does not process Bronze/Silver/Gold data, generate reports, run
AI logic, or connect to Spark or Azure.

The API loads events from `data/bronze/glims_lab_results.jsonl`. If the full
local file is not present, it falls back to
`samples/glims_lab_results_sample.jsonl`.

Run it from the repository root:

```powershell
cd C:\Users\Hp\Desktop\BioLab\BioLab-Project
uvicorn fake_glims_api.app.main:app --reload
```

If your terminal is currently in the parent `BioLab` folder, run:

```powershell
uvicorn --app-dir BioLab-Project fake_glims_api.app.main:app --reload
```

Endpoints:

```text
GET  /
GET  /health
GET  /patients
GET  /patients/{patient_id}/orders
GET  /patients/{patient_id}/results
GET  /orders/{order_id}/results
GET  /results?modified_after=2020-01-01T00:00:00Z
POST /simulate/new-result
POST /simulate/update-result
POST /simulate/validate-result
POST /stream/patient/{patient_id}
POST /stream/all?limit=100
POST /stream/modified?modified_after=2020-01-01T00:00:00Z
```

The API exposes only pseudonymized `patient_id` values already present in the
fake GLIMS events. It adds stable `result_id` values when missing and uses
`modified_at` timestamps for polling-style simulations.

`POST /stream/patient/{patient_id}` returns the events that would be streamed.
When `KAFKA_ENABLED=true`, stream endpoints publish to local Kafka/Redpanda
topics; otherwise they return `kafka_publishing_enabled: false` and do not
publish.

## Local Kafka / Redpanda Streaming

Redpanda provides a local Kafka-compatible broker for testing the integration
path from the Fake GLIMS API into future streaming ingestion. This step only
publishes fake GLIMS events to Kafka topics; Spark, Databricks, Azure, AI report
generation, and dashboards are not implemented here.

Start Redpanda and Redpanda Console:

```powershell
docker compose up -d
```

Redpanda listens on `localhost:9092`. Redpanda Console is exposed at
`http://localhost:8080`.

Create the Kafka topics:

```powershell
python scripts/create_kafka_topics.py
```

Topics:

```text
glims.patient
glims.order
glims.specimen
glims.result
glims.validation
```

Enable Kafka publishing in `.env`:

```dotenv
KAFKA_ENABLED=true
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

Run the Fake GLIMS API:

```powershell
uvicorn fake_glims_api.app.main:app --reload
```

Stream one patient:

```text
POST /stream/patient/{patient_id}
```

Stream all currently loaded events, with an optional limit:

```text
POST /stream/all?limit=100
```

Stream modified events for polling-style GLIMS simulation:

```text
POST /stream/modified?modified_after=2020-01-01T00:00:00Z
```

Consume messages from a topic:

```powershell
python scripts/consume_kafka_topic.py --topic glims.result --max-messages 10
```

If `KAFKA_ENABLED=false`, the API remains fully usable and stream endpoints
return the events that would be streamed without publishing anything.

## Local PySpark Medallion Pipeline

The local PySpark pipeline prepares fake GLIMS result events for future
analytics and AI reporting. It writes three medallion layers locally:

```text
Bronze: raw parsed GLIMS events plus ingestion metadata
Silver: cleaned, normalized, latest lab results with simple abnormal flags
Gold: patient/order/specimen report context and dashboard KPIs
```

Outputs are written under:

```text
data/bronze/glims_events/
data/silver/lab_results/
data/gold/report_context/
data/gold/dashboard_kpis/
```

These folders remain local and Git-ignored.

Run JSONL development mode:

```powershell
python -m pipelines.spark.run_local_pipeline --source jsonl
```

JSONL mode reads `data/bronze/glims_lab_results.jsonl` when available and falls
back to `samples/glims_lab_results_sample.jsonl`. It is the easiest local
development path.

PySpark 3.3 with this project’s Python 3.7 environment requires Java 8, 11, or
17. Java 21+ can fail during Spark startup with low-level Hadoop/Spark JVM
errors. Check your Java version with:

```powershell
java -version
```

If it reports Java 21, 23, or newer, install a Java 17 JDK, set `JAVA_HOME` to
that JDK, update `PATH`, then run the pipeline again.

On Windows, Spark also needs Hadoop native helper files for local file writes.
Put matching Hadoop 3.x `winutils.exe` and `hadoop.dll` files here:

```text
hadoop/bin/winutils.exe
hadoop/bin/hadoop.dll
```

These binaries are intentionally ignored by Git. Use files from the same
winutils/Hadoop distribution; mixing versions can cause errors like
`NativeIO$Windows.access0`. You can also set `HADOOP_HOME` in `.env` to another
folder that contains both `bin/winutils.exe` and `bin/hadoop.dll`.

Run Kafka architecture mode:

```powershell
docker compose up -d
python scripts/create_kafka_topics.py
uvicorn fake_glims_api.app.main:app --reload
```

Then stream events from the API:

```text
POST /stream/all?limit=100
```

Finally run:

```powershell
python -m pipelines.spark.run_local_pipeline --source kafka
```

Kafka mode reads from the local Redpanda topic `glims.result`. If Spark Kafka
dependencies or the local broker are unavailable, the pipeline falls back to
JSONL mode for development.

The current Gold report context is marked `READY_FOR_AI` when it contains at
least one lab result, but no AI report generation is implemented in this part.

## AI Backend and Report-first Workflow

The AI backend reads Gold report contexts from `data/gold/report_context/`,
generates AI draft biological reports with a mock MedGemma provider, stores
reports and report versions in a local SQLite application database, and enforces
the report-first workflow.

The chatbot is locked until a report exists. A biologist must generate an AI
draft report first; only then can `/reports/{report_id}/chat` be used for that
report. If the Gold context changes and the stored report context hash no
longer matches, the report is marked `OUTDATED`, validation is blocked, and chat
is blocked until regeneration.

The local database lives at:

```text
app_state/biolab_local.db
```

`app_state/` remains Git-ignored.

The mock provider in `ai_backend/app/ai_providers/mock_medgemma.py` creates a
professional structured draft using only pseudonymized IDs and Gold context
fields. It does not provide definitive diagnoses and can later be replaced by a
real local or cloud provider such as `local_medgemma.py` or
`azure_medgemma.py`.

Run the AI backend:

```powershell
uvicorn ai_backend.app.main:app --reload --port 8001
```

Example workflow:

```text
1. Run the PySpark medallion pipeline first.
2. Start the AI backend.
3. GET  /cases
4. POST /reports/generate
5. GET  /reports/{report_id}
6. POST /reports/{report_id}/chat
7. POST /reports/{report_id}/validate
```

Useful endpoints:

```text
GET  /health
GET  /cases
GET  /cases/{patient_id}/{order_id}?specimen_id=...
POST /reports/generate
POST /reports/{report_id}/regenerate
POST /reports/{report_id}/check-outdated
POST /reports/{report_id}/validate
POST /reports/{report_id}/reject
GET  /reports
GET  /reports/{report_id}
POST /reports/{report_id}/chat
GET  /reports/{report_id}/chat
```
