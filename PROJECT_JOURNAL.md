# Carelane project journal

- **Project:** AI-assisted healthcare guidance, appointment booking and queue estimation
- **Course:** UCS503P Software Engineering Project, Thapar Institute of Engineering and Technology
- **Team named in the project report:** Mayank Kalra, Pranshu Sharma and Shashwat Mishra
- **Journal started:** 14 September 2026

This is the **project-wide journal**. The entries before 14 September were reconstructed from saved source files, run logs, metrics and validation records. They are not presented as notes written on those earlier days. Machine timestamps and test results remain in the linked evidence files. The records establish what was built and run; they do not establish which individual team member performed each task. Team members should add their own verified contributions before submitting this as an individual-work record.

Problems, fixes and unresolved warnings are tracked separately in the [errors and corrections journal](ERRORS_AND_CORRECTIONS_JOURNAL.md).

## Project objective and scope

Carelane connects a patient's symptom description to ranked specialty guidance, a fictional doctor directory, demo appointment booking, check-in and simulated queue progress. The current implementation is a **local software engineering prototype**. It is not a diagnostic device, a real clinic directory, or a live hospital booking system. The client is React Native/Expo, the service is FastAPI, and appointment and session state is held in SQLite. The specialty model used by the app is the saved TF-IDF plus Logistic Regression pipeline; a separately trained DistilBERT model provides an experimental comparison. A CatBoost model estimates waiting time in a simulated queue.

## Milestone log

### Concept and requirements — date not established by saved records

The project combined healthcare guidance, appointment handling and queue estimation into one patient workflow. The requirements identified symptom input, specialty ranking, doctor discovery, booking and cancellation, session ownership, check-in, queue progression and waiting-time information. The supplied proposal and software engineering report describe the concept; the precise date of the first idea and individual contributions are not documented in this workspace.

**Design decision:** Keep medical guidance as a research prediction and keep booking and queue behavior clearly marked as demonstrations.

### 6 September 2026 — experiment environment and data preparation

- Created the separate `healthcare-ai` Python environment and training pipeline. The saved environment records Python 3.12, scikit-learn, PyTorch, Transformers, CatBoost and an NVIDIA RTX 4050 Laptop GPU.
- Downloaded the public `gretelai/symptom_to_diagnosis` dataset and the `distilbert-base-uncased` checkpoint. Revision and file checksum records were saved for reproducibility.
- Recovered a stalled CUDA wheel transfer with a range-based download script and verified the official SHA-256 before installation. The journal records this as setup recovery, not a failed model run.
- Prepared the 1,065-source-row text dataset. Five exact duplicates and seven training rows too similar to publisher-test records were excluded. The retained split contains **673 training**, **168 validation** and **212 test** records. The 22 condition labels were mapped to nine project-defined specialty labels.
- Generated a first-come, first-served queue simulation covering **12,150 visits**, 90 days and three departments. The queue data is synthetic.

**Evidence:** [training journal](TRAINING_JOURNAL.txt), [data audit](reports/data_audit.json), [environment](reports/environment.json), [download provenance](reports/download_provenance.json), [methods and limitations](reports/research_assets/METHODS_AND_LIMITATIONS.md).

### 6–7 September 2026 — model training and comparison

Four saved experiments were completed. The text baseline uses word and character TF-IDF features with balanced Logistic Regression; validation macro-F1 selected `C = 8`. DistilBERT was fine-tuned for nine specialty classes over eight epochs using class-weighted cross-entropy and mixed precision. CatBoost learned wait estimates from simulated queue-state features, with a chronological split and validation-based early stopping. The latest saved run summary is dated 7 September.

| Saved experiment | Test result | Recorded run duration |
| --- | ---: | ---: |
| Condition TF-IDF + Logistic Regression | 94.34% accuracy; 0.9430 macro-F1 | 5.97 s |
| Specialty TF-IDF + Logistic Regression | 96.70% accuracy; 0.9683 macro-F1 | 2.81 s |
| Specialty DistilBERT | 95.75% accuracy; 0.9596 macro-F1 | 94.79 s |
| Queue CatBoost | 5.464 min test MAE versus 6.378 min baseline MAE | 18.91 s |

The baseline specialty classifier achieved the highest first-ranked test accuracy and became the app's default model. DistilBERT achieved the higher **validation** macro-F1 in this single run. The CatBoost improvement is measured only against a baseline on simulated visits. Training durations include script execution, selection, evaluation and saving; they exclude installation and downloads.

**Evidence:** [run summary](reports/RUN_SUMMARY.txt), [timestamped events](reports/events.jsonl), [specialty baseline metrics](reports/specialty_baseline_metrics.json), [DistilBERT metrics](reports/specialty_distilbert_metrics.json), [queue metrics](reports/queue_catboost_metrics.json), [training journal](TRAINING_JOURNAL.txt). Model files are under `models/`.

### 7–9 September 2026 — research results and viewing tools

Saved metrics, row-level predictions, confusion matrices and training curves were assembled into a local visual research dashboard and offline research bundle. The dashboard provides a screen for reviewing model comparison, evaluation and logs. These displays use saved results; producing them did not constitute a new training run.

**Evidence:** [dashboard](reports/dashboard/index.html), [research assets](reports/research_assets), [report guide](REPORT_GUIDE.txt), [research bundle](reports/healthcare_research_bundle.zip).

### 9 September 2026 — patient application and backend

- Built the patient app with Expo SDK 57, React Native and TypeScript. Its sections cover Home, Find Care, My Visits and Live Queue.
- Added a FastAPI service and SQLite storage. Anonymous demo sessions link users to their appointments; the backend stores a hash of the session token.
- Connected symptom guidance to the saved specialty baseline model. Added fictional doctor/clinic search, candidate slots, booking, cancellation, check-in and simulated queue advancement.
- Added a request identifier for idempotent booking and a unique active doctor/slot constraint inside a transaction to protect against conflicting reservations.
- Limited CatBoost wait estimates to the three departments supported by the simulated training data.

**Verification recorded on 9 September:** Four backend tests passed, nine browser checks passed, TypeScript checking passed, and web and Android JavaScript/Hermes exports completed. The browser journey covered model inference, filtering, booking persistence after reload, check-in and queue completion. No physical Android installation or signed APK was verified.

**Evidence:** [app development journal](docs/APP_DEVELOPMENT_JOURNAL.md), [validation record](reports/app/VALIDATION.md), [browser checks](reports/app/browser-checks.json), [app README](APP_README.md), [screenshots](reports/app).

### 14 September 2026 — project report

A full project report and an Overleaf source package were produced from the implementation and saved results. The report documents requirements, architecture, UML/use case/activity/class/SDLC diagrams, training methods, evaluation, application validation and limitations. Its performance claims should be read with the small proxy-labeled text dataset and synthetic queue context beside them.

**Evidence:** [project report](output/report/Carelane_Project_Report.pdf), [Overleaf source package](output/report/Carelane_Overleaf_Source.zip), [LaTeX source](output/report/overleaf/main.tex). The user also supplied `SE (14).pdf` as a report source for the later presentation.

### 14 September 2026 — presentation

A **14-slide** PowerPoint presentation was exported from the project report. It includes five requested diagrams: system architecture, UML use case, activity, UML class and iterative SDLC. Structural package and slide-count validation passed. The user stopped the task before the planned visual inspection of every slide, so the deck should be reviewed visually before submission.

**Evidence:** [presentation](output/presentation/final/Carelane_Project_Presentation_2026.pptx), validation receipt at `output/presentation/.build/validation.json`.

### 14 September 2026 — consolidated journal created

This file brings the concept, model experiments, dashboard, application, report and presentation into one project record. It does not change prior training or app logs and does not claim that new model training occurred today.

## Current status

The local prototype demonstrates specialty guidance, fictional provider discovery, booking and a simulated patient queue. Saved ML metrics and software checks are available for documentation. The patient-facing features and model scores remain experimental. The current work has **not** established clinical safety, real provider integration, real hospital wait-time performance, production security, or a deployable signed Android app.

## Next work to record

1. Visually inspect and, if needed, revise the 14-slide presentation.
2. Test the app on a physical Android device and produce a signed build if required by the course.
3. Obtain clinician-reviewed, appropriately consented data and perform independent external evaluation before making healthcare claims.
4. Replace fictional provider and simulated queue data only after authorized integrations and privacy/security review.
5. Add verified team-member contributions and dates. Do not infer individual ownership from a planned work split.

## Template for future entries

Copy this block for each meaningful change so this journal stays current:

```text
Date and time:
Goal:
Work completed:
Tools / commands / model versions:
Data or artifact changed:
Validation and measured result:
Problems and decisions:
Limitations / next step:
Person(s) who actually performed the work:
Evidence path(s):
```
