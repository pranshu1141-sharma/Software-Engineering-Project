"""Queue simulation experiment, not measured hospital performance."""
import heapq
import time
import numpy as np
import pandas as pd
from catboost import CatBoostRegressor
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from .common import ROOT, SEED, environment, journal, source_hashes, write_json

FEATURES = ['department', 'patients_ahead', 'active_doctors', 'busy_doctors',
            'recent_mean_minutes', 'minute_of_session', 'day_of_week']


def simulate():
    rng = np.random.default_rng(SEED)
    rows = []
    # These are arbitrary simulator parameters, not clinical statistics.
    departments = {'General Medicine': 12.0, 'Dermatology': 10.0, 'Orthopedics': 16.0}
    for day in range(90):
        for department, typical in departments.items():
            doctors = int(rng.integers(1, 4))
            servers = [0.0] * doctors
            heapq.heapify(servers)
            visits = []
            arrival = 0.0
            session_speed = rng.uniform(0.8, 1.25)
            for person in range(45):
                arrival += float(rng.exponential(typical / doctors * rng.uniform(0.7, 1.2)))
                completed = sorted((v for v in visits if v['end'] <= arrival), key=lambda v: v['end'])
                recent = float(np.mean([v['duration'] for v in completed[-10:]])) if completed else typical
                ahead = sum(v['start'] > arrival for v in visits)
                busy = sum(v['start'] <= arrival < v['end'] for v in visits)
                available = heapq.heappop(servers)
                start = max(arrival, available)
                duration = float(rng.lognormal(np.log(typical * session_speed) - 0.35 ** 2 / 2, 0.35))
                end = start + duration
                heapq.heappush(servers, end)
                rows.append({'session_id': f'{day:03d}-{department}', 'day_index': day,
                             'department': department, 'patients_ahead': ahead, 'active_doctors': doctors,
                             'busy_doctors': busy, 'recent_mean_minutes': recent,
                             'minute_of_session': arrival, 'day_of_week': day % 7,
                             'wait_minutes': start - arrival,
                             'baseline_minutes': (ahead + 0.5 * busy) * recent / doctors if busy == doctors else 0.0})
                visits.append({'start': start, 'end': end, 'duration': duration})
    return pd.DataFrame(rows)


def train():
    begin = time.perf_counter()
    journal('TRAINING_STARTED', {'model': 'queue_catboost', 'data': '12,150 locally simulated FCFS visits; no hospital data',
                                 'method': 'Gradient-boosted regression trees; chronological split by whole day/session'})
    frame = simulate()
    frame.to_csv(ROOT / 'data/processed/queue_simulated.csv', index=False)
    train = frame[frame.day_index < 60]
    val = frame[(frame.day_index >= 60) & (frame.day_index < 75)]
    test = frame[frame.day_index >= 75]
    model = CatBoostRegressor(iterations=500, depth=6, learning_rate=0.05, loss_function='MAE',
                              random_seed=SEED, thread_count=4, verbose=False, allow_writing_files=False)
    model.fit(train[FEATURES], train.wait_minutes, cat_features=['department'],
              eval_set=(val[FEATURES], val.wait_minutes), early_stopping_rounds=40, use_best_model=True)
    pred = np.maximum(0, model.predict(test[FEATURES]))
    val_pred = np.maximum(0, model.predict(val[FEATURES]))
    output = ROOT / 'models/queue_catboost'
    output.mkdir(parents=True, exist_ok=True)
    model.save_model(str(output / 'model.cbm'))
    result = {'model': 'queue_catboost', 'status': 'SIMULATION_ONLY',
              'training_seconds': time.perf_counter() - begin,
              'split_rows': {'train': len(train), 'validation': len(val), 'test': len(test)},
              'features': FEATURES, 'best_iteration': model.get_best_iteration(),
              'validation_mae_minutes': mean_absolute_error(val.wait_minutes, val_pred),
              'validation_baseline_mae_minutes': mean_absolute_error(val.wait_minutes, val.baseline_minutes),
              'test_mae_minutes': mean_absolute_error(test.wait_minutes, pred),
              'test_rmse_minutes': root_mean_squared_error(test.wait_minutes, pred),
              'test_baseline_mae_minutes': mean_absolute_error(test.wait_minutes, test.baseline_minutes),
              'feature_importance': dict(zip(FEATURES, model.feature_importances_.tolist())),
              'hyperparameters': model.get_params(), 'environment': environment(), 'source_hashes': source_hashes(),
              'limitations': 'Learns this simulator. Does not prove real hospital accuracy or waiting-time reduction. No priority, breaks, emergencies, or cancellations modeled.'}
    write_json(output / 'metadata.json', result)
    write_json(ROOT / 'reports/queue_catboost_metrics.json', result)
    test.assign(predicted_minutes=pred).to_csv(ROOT / 'reports/queue_test_predictions.csv', index=False)
    journal('TRAINING_COMPLETED', {k: v for k, v in result.items() if k not in ['source_hashes', 'environment', 'feature_importance', 'hyperparameters']})


if __name__ == '__main__':
    train()
