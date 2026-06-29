# Pre-Azure Checklist

## Data

- [ ] Fake GLIMS API works
- [ ] Kafka topics exist
- [ ] Pipeline produced Bronze output
- [ ] Pipeline produced Silver output
- [ ] Pipeline produced Gold output
- [ ] `data/gold/report_context/` exists and contains data

## AI

- [ ] Remote MedGemma server is reachable
- [ ] AI backend health shows `remote_medgemma`
- [ ] `REQUIRE_REAL_LLM=true`
- [ ] `is_real_llm=true`
- [ ] No mock fallback
- [ ] Report generation response shows `provider_used=remote_medgemma`
- [ ] Chat response shows `provider_used=remote_medgemma`

## Workflow

- [ ] Generate AI report
- [ ] Chat after report generation
- [ ] Check report is not outdated
- [ ] Validate report
- [ ] Generate final PDF
- [ ] Download PDF

## Frontend

- [ ] Cases page works
- [ ] Case detail page works
- [ ] Report detail page works
- [ ] Chat panel works
- [ ] Validate/reject/regenerate buttons work
- [ ] PDF button works
- [ ] Download PDF button works

## Evidence

- [ ] Swagger screenshots
- [ ] Dashboard screenshots
- [ ] Kafka consumer screenshot
- [ ] Pipeline output screenshot
- [ ] MedGemma Colab health screenshot
- [ ] Generated PDF screenshot/download
- [ ] `demo/output/pre_azure_validation_summary.json`
