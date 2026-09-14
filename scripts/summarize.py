import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from healthcare_ml.common import environment, journal, read_json, write_json


def main():
    lines = ['AI HEALTHCARE - ACTUAL TRAINING RESULTS', '',
             'All text results use the small public LLM-rewritten dataset.',
             'Specialty targets are unreviewed condition-derived proxies.',
             'Queue results are from a simulator, not hospital measurements.', '']
    inventory = []
    for name in ['condition_baseline', 'specialty_baseline', 'specialty_distilbert', 'queue_catboost']:
        path = ROOT / f'reports/{name}_metrics.json'
        if not path.exists():
            lines.extend([name + ': NOT COMPLETED', ''])
            continue
        result = read_json(path)
        lines.append(name + ': COMPLETED')
        lines.append(f"Measured training/evaluation run duration: {result['training_seconds']:.2f} seconds")
        if name == 'queue_catboost':
            lines.append(f"Test rows: {result['split_rows']['test']}")
            lines.append(f"CatBoost test MAE: {result['test_mae_minutes']:.3f} minutes")
            lines.append(f"Arithmetic baseline test MAE: {result['test_baseline_mae_minutes']:.3f} minutes")
        else:
            lines.append(f"Test rows: {result['test']['sample_size']}")
            lines.append(f"Test accuracy: {result['test']['accuracy']:.2%}")
            lines.append(f"Test macro-F1: {result['test']['macro_f1']:.4f}")
            lines.append(f"Test top-three accuracy: {result['test']['top3_accuracy']:.2%}")
            lines.append(f"Validation macro-F1: {result['validation']['macro_f1']:.4f}")
        lines.extend([f'Metrics: reports/{name}_metrics.json', f'Artifacts: models/{name}/', ''])
        inventory.append(name)
        card = ['MODEL CARD: ' + name, 'Status: educational research experiment',
                'Clinical validation: none', 'Actual result metadata:', json.dumps(result, indent=2),
                '\nSource data/card: data/raw/gretel/README.md',
                'Specialty mapping review status: config/specialty_mapping.json',
                'Do not interpret these metrics as medical diagnostic reliability.']
        (ROOT / f'models/{name}/MODEL_CARD.txt').write_text('\n'.join(card), encoding='utf-8')
    candidates = []
    for name in ['specialty_baseline', 'specialty_distilbert']:
        path = ROOT / f'reports/{name}_metrics.json'
        if path.exists():
            result = read_json(path)
            candidates.append((result['validation']['macro_f1'], name))
    if candidates:
        selected = max(candidates)[1]
        lines.extend(['Best specialty experiment by validation macro-F1: ' + selected,
                      'API baseline remains the explicit default; both can be requested.', ''])
    (ROOT / 'reports/RUN_SUMMARY.txt').write_text('\n'.join(lines), encoding='utf-8')
    write_json(ROOT / 'reports/environment.json', environment())
    manifest = {str(path.relative_to(ROOT)): read_json(path) for path in
                [ROOT / 'data/raw/gretel/download_manifest.json', ROOT / 'models/pretrained/distilbert/download_manifest.json']
                if path.exists()}
    write_json(ROOT / 'reports/download_provenance.json', manifest)
    journal('SUMMARY_WRITTEN', {'completed_models': inventory, 'report': 'reports/RUN_SUMMARY.txt'})
    print('\n'.join(lines))


if __name__ == '__main__':
    main()
