# Colab Quickstart for Remote MedGemma

This is the temporary pre-Azure path:

```text
Local PC: Fake GLIMS API, Kafka, PySpark pipeline, AI backend, SQLite
Colab GPU: MedGemma model server only
```

Later, the same local backend can point `MEDGEMMA_API_URL` to Azure ML, Azure AI
Foundry, or an Azure GPU VM.

## 1. Start a GPU runtime

In Colab:

```bash
!nvidia-smi
```

If no GPU appears, enable one from `Runtime > Change runtime type > GPU`.

## 2. Get the code

Clone the repository or upload it to Colab:

```bash
!git clone https://github.com/aminebouanani/BioLab-Project.git
%cd BioLab-Project
```

## 3. Install server dependencies

```bash
!pip install -r medgemma_server/requirements.txt
```

## 4. Authenticate to Hugging Face

If you have `HF_TOKEN`, set it:

```python
import os
os.environ["HF_TOKEN"] = "PASTE_YOUR_HF_TOKEN"
```

Or log in interactively:

```bash
!huggingface-cli login
```

Make sure your Hugging Face account has access to the MedGemma model.

## 5. Start the server

```python
import os, subprocess, time
os.environ["MEDGEMMA_MODEL_ID"] = "google/medgemma-4b-it"
os.environ["MEDGEMMA_MAX_NEW_TOKENS"] = "700"
os.environ["MEDGEMMA_TEMPERATURE"] = "0.2"

server = subprocess.Popen([
    "uvicorn", "medgemma_server.app:app",
    "--host", "0.0.0.0",
    "--port", "9000"
])
time.sleep(5)
```

## 6. Expose with cloudflared

```bash
!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O cloudflared
!chmod +x cloudflared
```

```python
import subprocess, time, re
tunnel = subprocess.Popen(
    ["./cloudflared", "tunnel", "--url", "http://localhost:9000"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)
public_url = None
for _ in range(60):
    line = tunnel.stdout.readline()
    print(line, end="")
    match = re.search(r"https://[-a-zA-Z0-9.]+trycloudflare.com", line)
    if match:
        public_url = match.group(0)
        break
print("PUBLIC_URL=", public_url)
```

Ngrok also works, but may require an auth token.

## 7. Test inside Colab

```python
import requests, json
print(requests.get(public_url + "/health").json())

payload = {
    "context": {
        "patient_id": "PAT-sample",
        "order_id": "ORD-sample",
        "specimen_id": "SPC-sample",
        "results_count": 1,
        "abnormal_results_count": 1,
        "normal_results_count": 0,
        "unknown_flag_results_count": 0,
        "validation_status_summary": "FINAL",
        "context_hash": "sample-context-hash",
        "results": [{
            "test_name": "Glucose",
            "loinc_code": "2345-7",
            "value_raw": "160",
            "unit": "mg/dL",
            "reference_range": "70-110",
            "abnormal_flag": "H",
            "validation_status": "FINAL",
            "result_datetime": "2026-01-01T10:00:00Z"
        }]
    },
    "instructions": "Generate a structured AI draft biological report using only the provided context."
}
print(requests.post(public_url + "/generate-report", json=payload, timeout=180).json())
```

## 8. Run the local backend against Colab

On your Windows PC, in PowerShell:

```powershell
$env:AI_PROVIDER="remote_medgemma"
$env:AI_PROVIDER_FALLBACK_TO_MOCK="false"
$env:REQUIRE_REAL_LLM="true"
$env:MEDGEMMA_API_URL="<public_url>"
uvicorn ai_backend.app.main:app --reload --port 8001
```

Then run:

```powershell
python scripts/test_remote_medgemma_provider.py
python scripts/test_full_app_real_llm.py
```

The final test is successful only when the backend reports:

```text
active_provider=remote_medgemma
require_real_llm=true
is_real_llm=true
```
