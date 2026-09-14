import numpy as np
import pandas as pd
import pytest
from fastapi.testclient import TestClient
from healthcare_ml.api import app
from healthcare_ml.common import ROOT, read_json, remove_condition_names
from healthcare_ml.predict import load_baseline

client = TestClient(app)


def test_no_exact_or_near_duplicate_groups_cross_splits():
    frames = [pd.read_csv(ROOT / f'data/processed/{name}.csv') for name in ['train', 'validation', 'test']]
    for i, left in enumerate(frames):
        for right in frames[i + 1:]:
            assert not set(left.text_sha256) & set(right.text_sha256)
            assert not set(left.group_id) & set(right.group_id)
    assert len(set(frames[0].condition)) == 22


def test_negations_survive_condition_name_removal():
    result = remove_condition_names('No fever. I have diabetes but no cough.', ['diabetes'])
    assert 'diabetes' not in result
    assert 'no fever' in result and 'no cough' in result


@pytest.mark.parametrize('target', ['condition', 'specialty'])
def test_saved_baseline_matches_recorded_test_predictions(target):
    frame = pd.read_csv(ROOT / 'data/processed/test.csv')
    saved = pd.read_csv(ROOT / f'reports/{target}_baseline_test_predictions.csv')
    model = load_baseline(target)
    assert model.predict(frame.text).tolist() == saved.predicted.tolist()
    assert np.allclose(model.predict_proba(frame.text).sum(axis=1), 1)


def test_all_trained_artifacts_ready():
    assert client.get('/health').json()['status'] == 'ready'


@pytest.mark.parametrize('model', ['baseline', 'distilbert'])
def test_specialty_saved_model_api(model):
    response = client.post('/research/specialty', json={'text': 'My skin is itchy and has flaky patches.', 'model': model})
    assert response.status_code == 200
    result = response.json()
    assert result['research_only'] and result['requires_professional_review']
    assert len(result['ranked_labels']) == 3
    assert result['ranked_labels'][0]['model_score'] >= result['ranked_labels'][1]['model_score']


@pytest.mark.parametrize('text', ['', '          ', 'diabetes diabetes', 'x' * 2001])
def test_invalid_symptom_input_rejected(text):
    assert client.post('/research/specialty', json={'text': text}).status_code == 422


def test_condition_transformer_rejected():
    assert client.post('/research/conditions', json={'text': 'I have a cough and fever.', 'model': 'distilbert'}).status_code == 422


QUEUE = {'department': 'General Medicine', 'patients_ahead': 3, 'active_doctors': 2,
         'busy_doctors': 2, 'recent_mean_minutes': 12, 'minute_of_session': 90, 'day_of_week': 1}


def test_queue_prediction_and_input_constraints():
    result = client.post('/research/queue', json=QUEUE)
    assert result.status_code == 200
    assert result.json()['estimated_minutes'] >= 0
    assert result.json()['real_hospital_validated'] is False
    for patch in [{'active_doctors': 0}, {'busy_doctors': 3}, {'patients_ahead': -1},
                  {'busy_doctors': 1}, {'department': 'Unknown'}]:
        assert client.post('/research/queue', json={**QUEUE, **patch}).status_code == 422


def test_queue_whole_sessions_are_chronological():
    frame = pd.read_csv(ROOT / 'data/processed/queue_simulated.csv')
    train, val, test = frame[frame.day_index < 60], frame[(frame.day_index >= 60) & (frame.day_index < 75)], frame[frame.day_index >= 75]
    assert train.day_index.max() < val.day_index.min() < test.day_index.min()
    assert not set(train.session_id) & set(test.session_id)
    metadata = read_json(ROOT / 'reports/queue_catboost_metrics.json')
    assert 'wait_minutes' not in metadata['features']
    assert 'baseline_minutes' not in metadata['features']
