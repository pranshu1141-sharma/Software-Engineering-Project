# Healthcare AI model workspace

This repository contains the Carelane patient app, local API, model experiments,
saved results, report and presentation. For the full prototype workflow, see
`APP_README.md`. For team work, see `CONTRIBUTING.md`, `PROJECT_JOURNAL.md`
and `ERRORS_AND_CORRECTIONS_JOURNAL.md`.

## Visual report

Double-click `OPEN_REPORT.bat` to view the report page locally. It contains model
comparisons, training curves, confusion matrices, prediction errors and run logs.
Read `REPORT_GUIDE.txt` for export instructions. `reports/healthcare_research_bundle.zip`
contains the offline report, PNG/SVG figures, CSV/LaTeX tables and methods notes.
Rebuild the report from saved results using `.\.venv\Scripts\python.exe scripts\build_report.py`.

This folder contains the first reproducible model experiments for the merged
healthcare project. The website and mobile application can later share this API.

Read **MODELS_AND_TOOLS.txt**, **TWO_PERSON_WORK_SPLIT.txt**,
**TRAINING_JOURNAL.txt**, and **reports/RUN_SUMMARY.txt** first.
If a background GPU job is active, **GPU_JOB_STATUS.txt** shows its current
stage and **logs/gpu_job.log** records download, installation and training output.
Keep the laptop awake and connected until its status becomes `completed`.
Do not launch a second training/setup run while that job is active.

## What is implemented

- Public dataset and pretrained model downloader with revisions and checksums.
- Condition and specialty TF-IDF/Logistic Regression training.
- Local GPU DistilBERT specialty fine-tuning with validation checkpoint selection.
- Queue simulator, arithmetic baseline and CatBoost wait regression.
- Metrics, per-class reports, confusion matrices and row-level predictions.
- Local FastAPI research endpoints and integration/data leakage tests.

The specialty mapping is **unreviewed**. The source descriptions are LLM-rewritten
and limited to 22 conditions. The queue model is trained on **simulated sessions**.
This is a model-development prototype; it does not provide validated medical routing,
diagnosis, emergency detection, production authentication or clinical deployment.
Inputs outside the dataset's scope may still receive incorrect ranked labels.

## Run from this folder in PowerShell

The environment is separate from the parent J.A.R.V.I.S project.

```powershell
# Initial setup on a Windows machine with Python 3.12 and an NVIDIA GPU:
.\setup.ps1

# Reproduce all experiments (overwrites latest artifacts/reports and appends journal):
.\run_training.ps1

# Faster baseline/queue-only development:
.\run_training.ps1 -SkipTransformer

# Inspect a saved text model:
.\.venv\Scripts\python.exe -m healthcare_ml.predict --text "My skin is itchy and has flaky patches."
.\.venv\Scripts\python.exe -m healthcare_ml.predict --model distilbert --text "My skin is itchy and has flaky patches."

# Run tests after all models have completed:
.\.venv\Scripts\python.exe -m pytest -q

# Local research API (leave this terminal running):
.\.venv\Scripts\python.exe -m uvicorn healthcare_ml.api:app --host 127.0.0.1 --port 8000
```

API documentation: http://127.0.0.1:8000/docs while the service is running.
Endpoints: `/health`, `/research/specialty`, `/research/conditions`, `/research/queue`.
Models load from disk and prediction requires no network requests.

## Reproducibility and evidence

`requirements-lock.txt` captures the actual installed environment.
`reports/download_provenance.json` records downloaded revisions and SHA256 values.
`reports/data_audit.json` records cleaning and exact split sizes.
`reports/*_metrics.json` includes settings and source hashes at training time.
`models/*/MODEL_CARD.txt` records each completed experiment and limitations.
`reports/events.jsonl` and the text journal keep an append-only event history.

The latest artifacts are overwritten by a rerun. Copy the model/report folders
before an experiment when you need to retain multiple full checkpoints.
Never load externally supplied pickle/joblib model files; these files are
locally generated and trusted only within this project.

## Next data milestone

Obtain reviewed specialty-routing cases and real or approved de-identified queue
timestamps. Replace proxy labels and simulator records, repeat the split audit,
calibrate scores and perform external evaluation before patient-facing use.
