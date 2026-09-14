import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, f1_score
from .common import ROOT, write_json


def classify_metrics(y_true, scores, labels):
    predicted = np.asarray(labels)[np.argmax(scores, axis=1)]
    top3 = np.argsort(scores, axis=1)[:, -min(3, len(labels)):]
    positions = {label: i for i, label in enumerate(labels)}
    hit = [positions[label] in indices for label, indices in zip(y_true, top3)]
    return {'accuracy': float(accuracy_score(y_true, predicted)),
            'macro_f1': float(f1_score(y_true, predicted, labels=labels, average='macro', zero_division=0)),
            'top3_accuracy': float(np.mean(hit)), 'sample_size': len(y_true),
            'classification_report': classification_report(y_true, predicted, labels=labels, output_dict=True, zero_division=0),
            'confusion_matrix': confusion_matrix(y_true, predicted, labels=labels).tolist(),
            'label_order': list(labels)}


def save_predictions(name, frame, target, scores, labels):
    ranked = np.argsort(-scores, axis=1)[:, :3]
    result = pd.DataFrame({'source_id': frame.source_id, 'group_id': frame.group_id,
                           'text': frame.text, 'expected': frame[target],
                           'predicted': [labels[i[0]] for i in ranked],
                           'top3': [' | '.join(labels[j] for j in i) for i in ranked]})
    result['correct'] = result.expected == result.predicted
    result.to_csv(ROOT / f'reports/{name}_test_predictions.csv', index=False)
    return result
