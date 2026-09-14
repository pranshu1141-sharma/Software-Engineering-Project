"""Create shareable research figures from recorded results, without retraining."""
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'reports/figures'
OUTPUT.mkdir(parents=True, exist_ok=True)
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})


def read(name):
    return json.loads((ROOT / f'reports/{name}_metrics.json').read_text(encoding='utf-8'))


def main():
    names = ['specialty_baseline', 'specialty_distilbert']
    data = [read(name) for name in names]
    fig, ax = plt.subplots(figsize=(8, 5))
    x = np.arange(2)
    for offset, key, label, color in [(-0.18, 'validation', 'Validation macro-F1', '#156a86'),
                                     (0.18, 'test', 'Test macro-F1', '#e99547')]:
        bars = ax.bar(x + offset, [r[key]['macro_f1'] for r in data], 0.34, label=label, color=color)
        ax.bar_label(bars, fmt='%.3f', padding=3)
    ax.set_xticks(x, ['TF-IDF + Logistic Regression', 'Fine-tuned DistilBERT'])
    ax.set_ylim(0, 1.12)
    ax.set_ylabel('Macro-F1')
    ax.set_title('Specialty classification experiment\nUnreviewed proxy labels; public LLM-rewritten text')
    ax.legend(loc='lower right')
    fig.tight_layout()
    fig.savefig(OUTPUT / 'specialty_comparison.png', dpi=160)
    plt.close(fig)

    selected = max(data, key=lambda r: r['validation']['macro_f1'])
    matrix = np.asarray(selected['test']['confusion_matrix'])
    labels = selected['test']['label_order']
    fig, ax = plt.subplots(figsize=(10, 9))
    im = ax.imshow(matrix, cmap='Blues')
    ax.set_xticks(range(len(labels)), labels, rotation=45, ha='right')
    ax.set_yticks(range(len(labels)), labels)
    for row in range(len(labels)):
        for col in range(len(labels)):
            ax.text(col, row, str(matrix[row, col]), ha='center', va='center',
                    color='white' if matrix[row, col] > matrix.max() / 2 else 'black')
    ax.set_xlabel('Predicted proxy label')
    ax.set_ylabel('Dataset-derived proxy label')
    ax.set_title(f"Held-out test confusion matrix: {selected['model']}\nSelected by validation macro-F1; not clinical validation")
    fig.colorbar(im, ax=ax, label='Examples')
    fig.tight_layout()
    fig.savefig(OUTPUT / 'specialty_confusion_matrix.png', dpi=160)
    plt.close(fig)

    queue = pd.read_csv(ROOT / 'reports/queue_test_predictions.csv')
    result = read('queue_catboost')
    fig, ax = plt.subplots(figsize=(7, 6))
    ax.scatter(queue.wait_minutes, queue.predicted_minutes, s=9, alpha=0.25, color='#156a86')
    limit = max(queue.wait_minutes.max(), queue.predicted_minutes.max())
    ax.plot([0, limit], [0, limit], color='#e99547', label='Perfect estimate')
    ax.set_xlabel('Actual wait in simulation (minutes)')
    ax.set_ylabel('Predicted wait (minutes)')
    ax.set_title(f"SIMULATED queues: held-out sessions\nCatBoost MAE {result['test_mae_minutes']:.2f} min; baseline {result['test_baseline_mae_minutes']:.2f} min")
    ax.legend()
    fig.tight_layout()
    fig.savefig(OUTPUT / 'queue_simulation_results.png', dpi=160)
    plt.close(fig)
    print(f'Wrote 3 figures to {OUTPUT}')


if __name__ == '__main__':
    main()
