# Run the Full Local Stack

Use separate terminals so each service stays visible.

## Terminal 1 - Redpanda

```powershell
docker compose up -d
python scripts/create_kafka_topics.py
```

## Terminal 2 - Fake GLIMS API

```powershell
uvicorn fake_glims_api.app.main:app --reload --port 8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Terminal 3 - Stream Events

Use Swagger or PowerShell:

```text
POST http://127.0.0.1:8000/stream/all?limit=100
```

Optional consumer:

```powershell
python scripts/consume_kafka_topic.py --topic glims.result --max-messages 10
```

## Terminal 4 - PySpark Medallion Pipeline

Development JSONL mode:

```powershell
python -m pipelines.spark.run_local_pipeline --source jsonl
```

Kafka architecture mode:

```powershell
python -m pipelines.spark.run_local_pipeline --source kafka
```

Expected outputs:

```text
data/bronze/glims_events/
data/silver/lab_results/
data/gold/report_context/
data/gold/dashboard_kpis/
```

## Terminal 5 - Remote MedGemma Server

Run this on Colab or another GPU host using:

```text
medgemma_server/colab_medgemma_server.ipynb
medgemma_server/colab_quickstart.md
```

Copy the public URL printed by cloudflared/ngrok.

## Terminal 6 - AI Backend With Real LLM

PowerShell:

```powershell
$env:AI_PROVIDER="remote_medgemma"
$env:AI_PROVIDER_FALLBACK_TO_MOCK="false"
$env:REQUIRE_REAL_LLM="true"
$env:MEDGEMMA_API_URL="<public_colab_or_gpu_url>"
uvicorn ai_backend.app.main:app --reload --port 8001
```

Health:

```text
http://127.0.0.1:8001/health
```

You must see:

```text
active_provider=remote_medgemma
require_real_llm=true
is_real_llm=true
```

## Terminal 7 - React Dashboard

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

## Validation Scripts

```powershell
python scripts/demo/check_services.py
python scripts/demo/run_pre_azure_validation.py
python scripts/demo/generate_demo_summary.py
```
