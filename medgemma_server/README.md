# Remote MedGemma Server

This folder contains a standalone FastAPI server for running real MedGemma on a
GPU host. The local BioLab AI backend calls this service with `MEDGEMMA_API_URL`.

The first intended runtime is Google Colab GPU. The same HTTP interface can later
run on Azure ML, Azure AI Foundry, an Azure GPU VM, RunPod, Modal, Kaggle, or any
other GPU-backed endpoint.

## Endpoints

```text
GET  /health
POST /generate-report
POST /answer-question
```

The server returns `is_real_llm=true` only when the real model is loaded and used.
It does not fake successful real-LLM responses.

## Environment

```bash
MEDGEMMA_MODEL_ID=google/medgemma-4b-it
MEDGEMMA_MAX_NEW_TOKENS=700
MEDGEMMA_TEMPERATURE=0.2
MEDGEMMA_DEVICE=auto
MEDGEMMA_API_KEY=
HF_TOKEN=
```

`HF_TOKEN` may be required depending on the model access terms on Hugging Face.

## Run

```bash
pip install -r medgemma_server/requirements.txt
uvicorn medgemma_server.app:app --host 0.0.0.0 --port 9000
```

If `MEDGEMMA_API_KEY` is set, clients must send:

```text
Authorization: Bearer <MEDGEMMA_API_KEY>
```

## Test

```bash
curl http://127.0.0.1:9000/health
curl -X POST http://127.0.0.1:9000/generate-report \
  -H "Content-Type: application/json" \
  --data @medgemma_server/sample_generate_report_request.json
```

For Colab, use `colab_quickstart.md` or `colab_medgemma_server.ipynb`.
