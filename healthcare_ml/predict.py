"""Local research predictions from saved artifacts; no autonomous care decisions."""
import argparse
from functools import lru_cache
import json
import numpy as np
import pandas as pd
import joblib
from .common import ROOT, read_json, remove_condition_names


@lru_cache(maxsize=4)
def load_baseline(target):
    return joblib.load(ROOT / f'models/{target}_baseline/model.joblib')


@lru_cache(maxsize=1)
def load_transformer():
    from transformers import AutoTokenizer, AutoModelForSequenceClassification
    path = ROOT / 'models/specialty_distilbert'
    model = AutoModelForSequenceClassification.from_pretrained(path, local_files_only=True)
    model.eval()
    return AutoTokenizer.from_pretrained(path, local_files_only=True), model


def predict_text(text, target='specialty', model_name='baseline'):
    labels = read_json(ROOT / 'data/processed/labels.json')
    clean = remove_condition_names(text, labels['condition'])
    if len(clean.strip()) < 10:
        raise ValueError('Enter at least 10 characters of symptom description after removing condition names.')
    if model_name == 'distilbert':
        if target != 'specialty':
            raise ValueError('DistilBERT was trained for specialty proxies only.')
        import torch
        tokenizer, model = load_transformer()
        inputs = tokenizer(clean, return_tensors='pt', truncation=True, max_length=128)
        with torch.inference_mode():
            scores = model(**inputs).logits.softmax(-1)[0].numpy()
        classes = [model.config.id2label[i] for i in range(len(scores))]
    else:
        model = load_baseline(target)
        scores = model.predict_proba([clean])[0]
        classes = model.classes_.tolist()
    ranked = np.argsort(-scores)[:3]
    return {'task': target, 'model': model_name, 'research_only': True,
            'requires_professional_review': True,
            'label_status': 'unreviewed condition-derived specialty proxy' if target == 'specialty' else 'small public research dataset condition label',
            'score_meaning': 'uncalibrated classifier score, not a medical probability',
            'ranked_labels': [{'label': classes[i], 'model_score': round(float(scores[i]), 6)} for i in ranked]}


@lru_cache(maxsize=1)
def load_queue():
    from catboost import CatBoostRegressor
    model = CatBoostRegressor()
    model.load_model(str(ROOT / 'models/queue_catboost/model.cbm'))
    return model


def predict_queue(values):
    from .train_queue import FEATURES
    prediction = max(0.0, float(load_queue().predict(pd.DataFrame([values])[FEATURES])[0]))
    return {'estimated_minutes': round(prediction, 2), 'model': 'queue_catboost',
            'research_only': True, 'training_data': 'simulated FCFS sessions',
            'real_hospital_validated': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--text', required=True)
    parser.add_argument('--target', choices=['condition', 'specialty'], default='specialty')
    parser.add_argument('--model', choices=['baseline', 'distilbert'], default='baseline')
    args = parser.parse_args()
    print(json.dumps(predict_text(args.text, args.target, args.model), indent=2))
