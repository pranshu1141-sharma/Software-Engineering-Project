"""Build an offline experiment dashboard and paper assets from saved evidence.

This script reads completed results. It never trains models or modifies metrics.
"""
import base64
import csv
from datetime import datetime, timezone
import hashlib
import html
import io
import json
from pathlib import Path
import shutil
import zipfile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / 'reports'
ASSETS = REPORTS / 'research_assets'
ASSETS.mkdir(exist_ok=True)
NAMES = {'condition_baseline': 'Condition · TF-IDF + LR',
         'specialty_baseline': 'Specialty · TF-IDF + LR',
         'specialty_distilbert': 'Specialty · DistilBERT',
         'queue_catboost': 'Queue · CatBoost'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.spines.top': False,
                     'axes.spines.right': False, 'svg.fonttype': 'none', 'savefig.facecolor': 'white'})


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def save_figure(fig, name):
    fig.tight_layout(pad=1.5)
    fig.savefig(ASSETS / f'{name}.png', dpi=300, bbox_inches='tight')
    fig.savefig(ASSETS / f'{name}.svg', bbox_inches='tight')
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png', dpi=120, bbox_inches='tight')
    plt.close(fig)
    return 'data:image/png;base64,' + base64.b64encode(buffer.getvalue()).decode()


def main():
    metrics = {key: read(REPORTS / f'{key}_metrics.json') for key in NAMES}
    audit = read(REPORTS / 'data_audit.json')
    events = [json.loads(line) for line in (REPORTS / 'events.jsonl').read_text(encoding='utf-8').splitlines() if line.strip()]
    provenance = read(REPORTS / 'download_provenance.json')
    transformer = metrics['specialty_distilbert']
    best_specialty = max(['specialty_baseline', 'specialty_distilbert'], key=lambda k: metrics[k]['validation']['macro_f1'])
    queue = metrics['queue_catboost']
    images = {}
    # Separate targets: condition classification is not directly comparable with specialty classification.
    fig, ax = plt.subplots(figsize=(7.8, 4.5))
    specialties = [metrics['specialty_baseline'], transformer]
    for offset, split, color, label in [(-.19, 'validation', '#147d79', 'Validation'), (.19, 'test', '#5169b8', 'Test')]:
        bars = ax.bar(np.arange(2) + offset, [m[split]['macro_f1'] for m in specialties], .36, color=color, label=label)
        ax.bar_label(bars, fmt='%.3f', padding=4)
    ax.set(xticks=[0, 1], xticklabels=['TF-IDF + Logistic Regression', 'Fine-tuned DistilBERT'],
           ylabel='Macro-F1', ylim=(0, 1.12), title='Specialty classification: validation and test')
    ax.legend(loc='lower right', frameon=False)
    images['comparison'] = save_figure(fig, '01_specialty_comparison')

    history = pd.DataFrame(transformer['history'])
    history.to_csv(ASSETS / 'distilbert_epoch_history.csv', index=False)
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    axes[0].plot(history.epoch, history.train_loss, 'o-', color='#147d79')
    axes[0].set(xlabel='Epoch', ylabel='Weighted training loss', title='Training loss', xticks=history.epoch)
    axes[1].plot(history.epoch, history.validation_macro_f1, 's-', color='#5169b8', label='Macro-F1')
    axes[1].plot(history.epoch, history.validation_accuracy, 'o--', color='#bd7926', label='Accuracy')
    axes[1].set(xlabel='Epoch', ylabel='Validation score', ylim=(0, 1.02), title='Validation performance', xticks=history.epoch)
    axes[1].legend(frameon=False)
    for ax in axes:
        ax.grid(axis='y', alpha=.18)
    images['training'] = save_figure(fig, '02_distilbert_training_curves')

    predictions = {}
    table_rows = []
    for name in list(NAMES)[:3]:
        m = metrics[name]
        labels = m['test']['label_order']
        matrix = np.asarray(m['test']['confusion_matrix'])
        pd.DataFrame(matrix, index=labels, columns=labels).to_csv(ASSETS / f'{name}_confusion_matrix.csv')
        per_class = pd.DataFrame({label: m['test']['classification_report'][label] for label in labels}).T
        per_class.index.name = 'label'
        per_class.to_csv(ASSETS / f'{name}_per_class.csv')
        size = 12 if len(labels) > 10 else 8
        fig, ax = plt.subplots(figsize=(size, size - .5))
        im = ax.imshow(matrix, cmap='Blues')
        ax.set_xticks(range(len(labels)), labels, rotation=50, ha='right')
        ax.set_yticks(range(len(labels)), labels)
        for row in range(len(labels)):
            for col in range(len(labels)):
                ax.text(col, row, str(matrix[row, col]), ha='center', va='center', fontsize=8,
                        color='white' if matrix[row, col] > matrix.max() / 2 else '#223044')
        ax.set(xlabel='Predicted label', ylabel='Reference label', title=NAMES[name] + f' | test n={matrix.sum()}')
        fig.colorbar(im, ax=ax, fraction=.035, pad=.02, label='Examples')
        images[name] = save_figure(fig, f'03_{name}_confusion_matrix')
        frame = pd.read_csv(REPORTS / f'{name}_test_predictions.csv')
        predictions[name] = frame.to_dict(orient='records')
        shutil.copy2(REPORTS / f'{name}_test_predictions.csv', ASSETS)
        table_rows.append({'model': name, 'target': 'condition' if name.startswith('condition') else 'specialty_proxy',
                           'train_n': audit['split_counts']['train']['rows'], 'validation_n': audit['split_counts']['validation']['rows'],
                           'test_n': m['test']['sample_size'], 'validation_macro_f1': m['validation']['macro_f1'],
                           'test_accuracy': m['test']['accuracy'], 'test_macro_f1': m['test']['macro_f1'],
                           'test_top3_accuracy': m['test']['top3_accuracy'], 'run_seconds': m['training_seconds']})
    table = pd.DataFrame(table_rows)
    table.to_csv(ASSETS / 'classification_results.csv', index=False)
    # A LaTeX table without optional pandas styling dependencies.
    tex = ['\\begin{tabular}{lrrr}', '\\hline', 'Model & Accuracy & Macro-F1 & Top-3 \\\\', '\\hline']
    for row in table_rows:
        tex.append(f"{NAMES[row['model']].replace('·', '-')} & {row['test_accuracy']:.4f} & {row['test_macro_f1']:.4f} & {row['test_top3_accuracy']:.4f} " + r'\\')
    tex += ['\\hline', '\\end{tabular}', '% Different targets: do not directly rank condition versus specialty models.']
    (ASSETS / 'classification_results.tex').write_text('\n'.join(tex), encoding='utf-8')

    queue_predictions = pd.read_csv(REPORTS / 'queue_test_predictions.csv')
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.2))
    axes[0].scatter(queue_predictions.wait_minutes, queue_predictions.predicted_minutes, s=8, alpha=.3, color='#147d79')
    maximum = max(queue_predictions.wait_minutes.max(), queue_predictions.predicted_minutes.max())
    axes[0].plot([0, maximum], [0, maximum], '--', color='#637082')
    axes[0].set(xlabel='Actual simulated wait (min)', ylabel='Predicted wait (min)', title='Held-out simulated sessions')
    bars = axes[1].bar(['Arithmetic baseline', 'CatBoost'], [queue['test_baseline_mae_minutes'], queue['test_mae_minutes']], color=['#b6c1cb', '#147d79'])
    axes[1].bar_label(bars, fmt='%.2f min', padding=4)
    axes[1].set(ylabel='Mean absolute error (minutes)', title='Test error: lower is better', ylim=(0, queue['test_baseline_mae_minutes'] * 1.25))
    images['queue'] = save_figure(fig, '04_queue_simulation_results')
    pd.DataFrame([{'model': 'arithmetic_baseline', 'test_mae_minutes': queue['test_baseline_mae_minutes'], 'test_n': queue['split_rows']['test']},
                  {'model': 'catboost', 'test_mae_minutes': queue['test_mae_minutes'], 'test_n': queue['split_rows']['test']}]).to_csv(ASSETS / 'queue_results.csv', index=False)

    captions = f'''FIGURE CAPTIONS AND REPORTING NOTES

01_specialty_comparison: Validation and test macro-F1 for direct specialty
classification using TF-IDF/Logistic Regression and fine-tuned DistilBERT.
Labels are unreviewed condition-to-specialty proxies. Training n=673,
validation n=168, test n=212. One seed (42); no repeated-run error bars.

02_distilbert_training_curves: Weighted training loss and validation scores
across {transformer['config']['epochs']} fine-tuning epochs. Epoch {transformer['best_epoch']} had the best validation
macro-F1 and was selected before evaluating the test set. A validation-loss
curve is not shown because validation loss was not recorded.

03_*_confusion_matrix: Counts of reference versus predicted labels on the
held-out text test set (n=212). Condition and specialty are distinct targets.
Specialty reference labels are proxies, not independent clinician decisions.

04_queue_simulation_results: Actual versus predicted waiting time in held-out
synthetic FCFS sessions, plus test MAE comparison. Test n=2,025 visits across
45 department-day sessions. Observations within a session are dependent.
The lower prediction error is NOT a reduction in patient waiting time.

PNG exports are 300 dpi; SVG exports are vector graphics with editable text.
CSV exports contain the values behind the tables and plots. LaTeX table values
are fractions, not percentages. These are initial experimental results, not
evidence of clinical readiness or results from a real hospital pilot.
'''
    (ASSETS / 'FIGURE_CAPTIONS.txt').write_text(captions, encoding='utf-8')
    notes = f'''# Experimental methods and limitations

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
(6 GB VRAM), using {transformer['config']['epochs']} epochs, batch size 8, gradient accumulation 2,
maximum length 128 tokens, AdamW (learning rate 2e-5, weight decay 0.01),
weighted cross entropy and mixed precision. Epoch {transformer['best_epoch']}
was selected by validation macro-F1. Both specialty models used the same splits.
{NAMES[best_specialty]} had higher validation macro-F1 in this single experiment.

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
baseline compared three C values, whereas DistilBERT used {transformer['config']['epochs']} epochs, so
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
'''
    (ASSETS / 'METHODS_AND_LIMITATIONS.md').write_text(notes, encoding='utf-8')
    for name in ['data_audit.json', 'download_provenance.json', 'environment.json', 'events.jsonl',
                 'RUN_SUMMARY.txt', *[f'{key}_metrics.json' for key in NAMES]]:
        shutil.copy2(REPORTS / name, ASSETS / name)
    for name in ['TRAINING_JOURNAL.txt', 'MODELS_AND_TOOLS.txt', 'TWO_PERSON_WORK_SPLIT.txt', 'requirements-lock.txt']:
        shutil.copy2(ROOT / name, ASSETS / name)
    shutil.copy2(REPORTS / 'queue_test_predictions.csv', ASSETS)
    shutil.copy2(ROOT / 'config/specialty_mapping.json', ASSETS)
    shutil.copy2(ROOT / 'logs/gpu_job.log', ASSETS / 'gpu_job.log')
    source_dir = ASSETS / 'training_source'
    source_dir.mkdir(exist_ok=True)
    for file in (ROOT / 'healthcare_ml').glob('*.py'):
        shutil.copy2(file, source_dir / file.name)
    (ASSETS / 'training_source/README.txt').write_text('Snapshot of current source. Original per-run hashes are recorded in the metric JSON files. Compare hashes before claiming an exact historical source match.', encoding='utf-8')
    hashes = {str(p.relative_to(ASSETS)).replace('\\', '/'): hashlib.sha256(p.read_bytes()).hexdigest()
              for p in ASSETS.rglob('*') if p.is_file() and p.name != 'ASSET_SHA256.json'}
    (ASSETS / 'ASSET_SHA256.json').write_text(json.dumps(hashes, indent=2), encoding='utf-8')
    downloads = [{'name': str(p.relative_to(ASSETS)).replace('\\', '/'), 'bytes': p.stat().st_size}
                 for p in sorted(ASSETS.iterdir()) if p.is_file()]
    verified = [e for e in events if e['event'] == 'BACKGROUND_JOB_COMPLETED']
    data = {'metrics': metrics, 'audit': audit, 'events': events, 'names': NAMES,
            'predictions': predictions, 'images': images, 'downloads': downloads,
            'generated': datetime.now(timezone.utc).isoformat(), 'complete': bool(verified),
            'journal': (ROOT / 'TRAINING_JOURNAL.txt').read_text(encoding='utf-8'),
            'gpuLog': (ROOT / 'logs/gpu_job.log').read_text(encoding='utf-8'),
            'provenance': provenance}
    template = (ROOT / 'scripts/report_template.html').read_text(encoding='utf-8')
    encoded = json.dumps(data, ensure_ascii=False).replace('</', '<\\/')
    rendered = template.replace('__REPORT_DATA__', encoded)
    output = REPORTS / 'dashboard/index.html'
    output.parent.mkdir(exist_ok=True)
    output.write_text(rendered, encoding='utf-8')
    with zipfile.ZipFile(REPORTS / 'healthcare_research_bundle.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
        portable = rendered.replace('../healthcare_research_bundle.zip', '../research_assets/ASSET_SHA256.json')
        portable = portable.replace('Download research bundle', 'Download asset manifest').replace('Download complete bundle', 'Download asset manifest')
        archive.writestr('dashboard/index.html', portable)
        for file in ASSETS.rglob('*'):
            if file.is_file():
                archive.write(file, 'research_assets/' + str(file.relative_to(ASSETS)).replace('\\', '/'))
    print(json.dumps({'dashboard': str(output), 'research_assets': len(hashes),
                      'bundle': str(REPORTS / 'healthcare_research_bundle.zip')}, indent=2))


if __name__ == '__main__':
    main()
