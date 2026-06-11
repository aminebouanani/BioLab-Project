# BioLab Project

Cloud-native post-analytical biological reporting project. This first component
adapts local Synthea laboratory data into pseudonymized, fake GLIMS-like
`LAB_RESULT_CREATED` events. It does not yet include Kafka, Spark, Azure, AI, or a
frontend.

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
