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
