# BioLab Local Demo and Pre-Azure Validation

This folder documents the full local validation workflow before Azure migration.

The goal is to prove the complete system works locally with a real remote
MedGemma LLM, not only with the mock provider:

```text
Fake GLIMS API
-> Kafka / Redpanda
-> PySpark Bronze/Silver/Gold
-> AI Backend
-> Remote MedGemma real LLM
-> SQLite report workflow
-> Chatbot
-> Biologist validation
-> Final PDF export
-> React dashboard
```

Start with:

```text
demo/run_local_stack.md
```

Then run:

```powershell
python scripts/demo/check_services.py
python scripts/demo/seed_demo_data.py --run-pipeline
python scripts/demo/run_pre_azure_validation.py
python scripts/demo/generate_demo_summary.py
```

Evidence to capture:

```text
demo/pre_azure_checklist.md
demo/screenshots_checklist.md
demo/expected_outputs.md
```

Generated validation summaries are written to `demo/output/`, which is ignored
by Git.
