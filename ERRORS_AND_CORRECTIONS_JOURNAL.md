# Carelane errors and corrections journal

- **Project:** Carelane
- **Journal created:** 14 September 2026
- **Companion:** [project-wide journal](PROJECT_JOURNAL.md)

This file records problems, corrections and verification **separately** from the general project timeline and the model-training event log. Older entries were reconstructed from saved logs and files on 14 September; they are not contemporaneous handwritten notes. A warning, a wrong model prediction and an unfinished feature are different from a software crash. Their status is stated explicitly below. Do not assign an error or its correction to a team member unless that person confirms their contribution.

## Status at a glance

| ID | Date of evidence | Type | Problem or risk | Status |
| --- | --- | --- | --- | --- |
| EC-01 | 6 Sep 2026 | Confirmed setup interruption | Standard CUDA wheel download stalled | Corrected and verified |
| EC-02 | 6–7 Sep 2026 | Data-quality correction | Duplicate and near-test records could inflate text evaluation | Exclusions applied; residual risk remains |
| EC-03 | 6–9 Sep 2026 | Test warning | Two upstream deprecation warnings | Open; tests pass |
| EC-04 | 7 Sep 2026 | Local-server observation | Dashboard server logged 404 requests and a reset connection | Exact cause unrecorded; later QA passed |
| EC-05 | 9 Sep 2026 | Preventive software correction | Repeated requests or competing users could double-book a slot | Protection implemented and tested |
| EC-06 | 7–9 Sep 2026 | Model prediction errors | Some retained test rows were misclassified | Open research issue |
| EC-07 | 14 Sep 2026 | Confirmed export failure | Presentation import check lacked a runtime environment variable | Corrected and verified |
| EC-08 | 14 Sep 2026 | Layout warnings | Six connector-over-text warnings in diagrams | Open visual review |

## Detailed entries

### EC-01 — CUDA dependency download stalled

**Observed:** On 6 September, the normal `pip` transfer of the PyTorch CUDA wheel stalled before writing wheel bytes. An initial package-resolution attempt was cancelled before installation so the NVIDIA CUDA build could be installed first. No model-training failure was claimed for this setup step.

**Correction:** `scripts/download_cuda_wheel.py` resumed the same official PyTorch 2.7.1 CUDA 12.6 wheel in byte ranges. The downloaded file was checked against the SHA-256 published by the official PyTorch index before installation. CPU dependencies were installed independently while the wheel transfer proceeded.

**Verification:** The saved GPU log records a successful `torch-2.7.1+cu126` installation; the later DistilBERT experiment completed on the RTX 4050 GPU.

**Status:** Closed for this local environment. A fresh machine still needs its own dependency check.

**Evidence:** [training journal](TRAINING_JOURNAL.txt), [GPU log](logs/gpu_job.log), [download helper](scripts/download_cuda_wheel.py), [environment record](reports/environment.json).

### EC-02 — duplicate and near-test text records

**Observed:** The dataset audit found five exact duplicate rows and seven publisher-training rows linked by high text similarity to test records. Leaving them in training would weaken the independence of the held-out evaluation. This is a **data-quality correction**, not evidence that an earlier reported score was wrong.

**Correction:** The preparation pipeline removed the five exact duplicates, grouped text using character TF-IDF similarity at a 0.90 threshold and excluded the seven training rows linked to test groups. The publisher test partition remained held out. Final counts were 673 train, 168 validation and 212 test.

**Verification:** The [data audit](reports/data_audit.json) records the removal counts and partitions. Saved training metrics use the resulting split.

**Residual risk:** Similarity grouping cannot rule out all semantic paraphrases or artifacts from LLM-rewritten source text. No independent external test set is recorded.

**Evidence:** [methods and limitations](reports/research_assets/METHODS_AND_LIMITATIONS.md), [data audit](reports/data_audit.json), [training journal](TRAINING_JOURNAL.txt).

### EC-03 — upstream test deprecation warnings

**Observed:** The saved test logs show two warnings from the Starlette/FastAPI test-client dependency path: an `httpx`/`starlette.testclient` warning and an `anyio.abc.BlockingPortal` alias warning. They did not cause test failures.

**Correction:** No dependency update or code correction is evidenced in the saved records. Avoid reporting these as fixed.

**Verification:** The CPU run logged 12 passed and 2 deselected tests with 2 warnings; the later full GPU-stage run logged 14 passed with 2 warnings. The app validation also reports four backend tests passed with two upstream warnings.

**Status:** Open maintenance warning. Recheck with compatible upstream package versions during the next environment update.

**Evidence:** [CPU test log](logs/cpu_tests.log), [GPU log](logs/gpu_job.log), [app validation](reports/app/VALIDATION.md).

### EC-04 — local dashboard server request errors

**Observed:** The local report server's stderr log contains two HTTP 404 responses and one `ConnectionResetError` on 7 September. The log alone does not identify which user action caused the missing file requests or why the client connection closed.

**Correction:** No specific repair is documented. Do not infer that a code change fixed these requests.

**Later check:** Saved dashboard QA reports all five sections, 48 checked download links, CSV export, metrics, mobile overflow and zero JavaScript errors as passing. This supports the dashboard's later functionality but does not explain the earlier server messages.

**Status:** Cause unconfirmed; monitor if the local server is run again.

**Evidence:** [server stderr](logs/report_server_stderr.log), [dashboard verification](reports/report_qa/verification.json).

### EC-05 — duplicate and conflicting appointment reservations

**Risk:** A repeated booking request could create two appointments, or simultaneous requests could reserve the same doctor and time. The records document a preventive implementation, **not** an observed production incident.

**Correction:** Appointment creation uses an idempotency request identifier and a SQLite unique active doctor/time constraint inside a transaction. Appointment actions require ownership of the anonymous demo session. Cancellation and check-in transitions also use transactions.

**Verification:** Backend tests cover idempotency, competing reservations, session ownership and cancellation releasing a slot. The saved app validation records four passing backend tests and a browser journey in which a booking survives reload.

**Status:** Verified for the local prototype's tested cases; production concurrency and security are untested.

**Evidence:** [app development journal](docs/APP_DEVELOPMENT_JOURNAL.md), [app validation](reports/app/VALIDATION.md), [backend tests](tests/test_patient_api.py), [API implementation](healthcare_ml/patient_api.py).

### EC-06 — classification mistakes on the held-out test partition

**Observed:** Dashboard verification counted incorrect predictions on the retained test rows: 7 for specialty TF-IDF/Logistic Regression, 9 for specialty DistilBERT and 12 for the condition baseline. These are **model prediction errors**, not crashes or failed software checks.

**Correction:** No subsequent retraining or clinically reviewed label correction is recorded. The app continues to use the saved specialty baseline. Do not claim that the errors have been eliminated.

**Next investigation:** Review row-level failures and specialty labels with a qualified clinician, obtain independent data, then rerun the split audit and evaluation. Scores from the current proxy-labeled dataset cannot establish clinical routing accuracy.

**Status:** Open research issue.

**Evidence:** [dashboard verification](reports/report_qa/verification.json), [specialty baseline predictions](reports/specialty_baseline_test_predictions.csv), [DistilBERT predictions](reports/specialty_distilbert_test_predictions.csv), [methods and limitations](reports/research_assets/METHODS_AND_LIMITATIONS.md).

### EC-07 — presentation finalization environment variable missing

**Observed:** On 14 September, the first PowerPoint finalization run exported a candidate file, then the first-party import check failed with `RUNTIME_NODE_MODULES is required`. The failure was in the validation environment; it did not report a slide-content error.

**Correction:** The finalization command was rerun with `RUNTIME_NODE_MODULES` set to the bundled Node dependency path.

**Verification:** The next run passed first-party import, package integrity, slide count and declared font checks, and wrote the 14-slide PowerPoint file.

**Status:** Closed for the exported file. Visual slide review remained separate and was stopped at the user's request.

**Evidence:** [presentation validation receipt](output/presentation/.build/validation.json), [presentation](output/presentation/final/Carelane_Project_Presentation_2026.pptx).

### EC-08 — presentation diagram connector warnings

**Observed:** The presentation layout validator reported six `connector_over_text` warnings across slides 5, 7 and 8. It reported zero hard layout findings, but these warnings could affect readability.

**Correction:** None yet. The user stopped the presentation task before the planned full-size visual inspection and any layout repair.

**Next check:** Open the deck, inspect every slide at presentation size, and adjust diagram connectors or labels if any lines cross text. Re-export and rerun validation after changes.

**Status:** Open. Do not describe the presentation as visually verified.

**Evidence:** [validation receipt](output/presentation/.build/validation.json), [presentation](output/presentation/final/Carelane_Project_Presentation_2026.pptx).

## Known gaps that are not recorded as fixed errors

- The current provider directory is fictional. The [report source notes](output/report/overleaf/README.md) say a real-provider listing file was empty and redesigned components had not been integrated into the tested app. This is unfinished scope, not an error with a documented correction.
- The queue model learned from simulated visits. Real hospital waiting-time accuracy is unknown.
- No physical Android device test, signed APK, production authentication or formal security/privacy assessment is documented.
- The report's LaTeX log contains `Underfull \hbox` notices, while a PDF was produced. No confirmed content failure or specific formatting correction is documented in the saved record.

## Entry template for future work

```text
ID and date/time:
Type: failure / warning / data-quality issue / model error / preventive change
Observed symptom and reproduction steps:
Expected behavior:
Root cause (confirmed, suspected, or unknown):
Correction made:
Files or data changed:
Verification command and result:
Residual risk / status:
Person(s) who actually performed the correction:
Evidence paths:
```
