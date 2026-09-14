# Experimental methods and limitations

Report generated from saved training artifacts; no retraining was performed.

## Text experiments
Public dataset: gretelai/symptom_to_diagnosis. The publisher describes 1,065
English descriptions, 22 condition labels, and rewriting with an LLM from
Symptom2Disease. Publisher-declared license: Apache-2.0. Exact revisions and
checksums are in download_provenance.json.

Lowercasing, apostrophe/whitespace normalization and exact condition-name
removal were applied; negation words were retained. Five exact duplicates
were removed. Character TF-IDF similarity >=0.90 defined connected groups;
seven publisher-training records linked to test groups were excluded. The
publisher test partition was retained. Grouped training/validation partitions
contain 673 and 168 records; test contains 212. This text audit does not rule
out all semantic paraphrase leakage or language-generation artifacts.

The 9 specialty labels are an author-defined condition mapping, not reviewed
patient-specific routing annotations. The condition classifier has 22 labels.
Word (1-2 grams) and character (3-5 grams) TF-IDF features were fitted only on
training text. Balanced Logistic Regression compared C in [0.5, 2, 8] using
validation macro-F1; C=8 was selected for both targets.

DistilBERT was fine-tuned locally with PyTorch on an RTX 4050 Laptop GPU
(6 GB VRAM), using 8 epochs, batch size 8, gradient accumulation 2,
maximum length 128 tokens, AdamW (learning rate 2e-5, weight decay 0.01),
weighted cross entropy and mixed precision. Epoch 8
was selected by validation macro-F1. Both specialty models used the same splits.
Specialty · DistilBERT had higher validation macro-F1 in this single experiment.

## Queue experiment
The locally written FCFS simulator generated 12,150 visits over 90 days and
3 departments. Training used the first 60 days (8,100 visits); validation
and test each used 15 later days (2,025 visits). Features were department,
patients ahead, active and busy doctors, recent completed consultation mean,
elapsed session minutes and day of week. Future consultation durations were
not supplied as model inputs. CatBoost used MAE loss, depth 6, learning rate
0.05, up to 500 iterations and validation early stopping (40 rounds).

## Limits and appropriate claims
These results establish a functioning prototype pipeline. They do not
establish clinical safety, real-world diagnostic accuracy, clinician routing
agreement, or reduced hospital waiting time. Text scores use a small public
LLM-rewritten dataset; specialty labels are unreviewed proxies. Queue scores
measure learning of the simulator. No prospective hospital study, independent
external test set, subgroup analysis, probability calibration, multiple-seed
study, or statistical significance analysis was performed. No confidence
intervals are claimed. Report these limitations alongside the results.

Run durations include training, model selection/evaluation and saving within
the measured script; they exclude package installation and downloads. The
baseline compared three C values, whereas DistilBERT used 8 epochs, so
durations are not controlled hardware benchmarks.

## Reproducibility
See requirements-lock.txt, original metric JSON files, training source hashes,
data_audit.json, download_provenance.json, and TRAINING_JOURNAL.txt.
Use the two-person work allocation as a plan; record actual human contributions
separately. The initial scripts and runs were AI-assisted.

## Source references
- Dataset: https://huggingface.co/datasets/gretelai/symptom_to_diagnosis
- Pretrained model: https://huggingface.co/distilbert/distilbert-base-uncased
- Training framework: https://huggingface.co/docs/transformers/tasks/sequence_classification
- Text features: https://scikit-learn.org/stable/modules/feature_extraction.html
- CatBoost: https://catboost.ai/docs/en/concepts/python-reference_catboostregressor
