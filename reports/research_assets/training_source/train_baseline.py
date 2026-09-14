import time
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.pipeline import Pipeline, FeatureUnion
from sklearn.linear_model import LogisticRegression
from .common import ROOT, SEED, environment, journal, source_hashes, write_json
from .metrics import classify_metrics, save_predictions


def train():
    parts = {split: pd.read_csv(ROOT / f'data/processed/{split}.csv')
             for split in ['train', 'validation', 'test']}
    for target in ['condition', 'specialty']:
        name = target + '_baseline'
        begin = time.perf_counter()
        journal('TRAINING_STARTED', {'model': name, 'method': 'Word/character TF-IDF + balanced multinomial Logistic Regression',
                                     'environment': environment(), 'training_rows': len(parts['train'])})
        candidates = []
        best = None
        for c in [0.5, 2.0, 8.0]:
            model = Pipeline([
                ('features', FeatureUnion([
                    ('word', TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, max_features=20000)),
                    ('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), sublinear_tf=True, max_features=30000))])),
                ('classifier', LogisticRegression(C=c, class_weight='balanced', max_iter=1500, random_state=SEED))])
            model.fit(parts['train'].text, parts['train'][target])
            labels = model.classes_.tolist()
            validation = classify_metrics(parts['validation'][target], model.predict_proba(parts['validation'].text), labels)
            candidates.append({'C': c, 'validation_macro_f1': validation['macro_f1']})
            if best is None or validation['macro_f1'] > best[0]:
                best = (validation['macro_f1'], model, c, validation)
        _, model, c, validation = best
        output = ROOT / f'models/{name}'
        output.mkdir(parents=True, exist_ok=True)
        joblib.dump(model, output / 'model.joblib')
        labels = model.classes_.tolist()
        scores = model.predict_proba(parts['test'].text)
        results = {'model': name, 'target': target, 'training_seconds': time.perf_counter() - begin,
                   'selected_C': c, 'candidates': candidates, 'validation': validation,
                   'test': classify_metrics(parts['test'][target], scores, labels),
                   'label_status': 'unreviewed specialty proxy' if target == 'specialty' else 'publisher condition labels; research only',
                   'score_status': 'Uncalibrated model scores; not medical probabilities',
                   'environment': environment(), 'source_hashes': source_hashes()}
        write_json(output / 'metadata.json', results)
        write_json(ROOT / f'reports/{name}_metrics.json', results)
        save_predictions(name, parts['test'], target, scores, labels)
        journal('TRAINING_COMPLETED', {'model': name, 'training_seconds': results['training_seconds'],
                                      'selected_C': c, 'validation_macro_f1': validation['macro_f1'],
                                      'test_accuracy': results['test']['accuracy'],
                                      'test_macro_f1': results['test']['macro_f1'],
                                      'test_rows': len(parts['test']), 'artifact': str(output.relative_to(ROOT)),
                                      'limitations': results['label_status']})


if __name__ == '__main__':
    train()
