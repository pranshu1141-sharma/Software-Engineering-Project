"""Preserve the publisher test partition and remove near-duplicate training leakage."""
import hashlib
import numpy as np
import pandas as pd
from scipy.sparse.csgraph import connected_components
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.model_selection import StratifiedGroupKFold
from .common import ROOT, SEED, journal, read_json, remove_condition_names, write_json


def prepare():
    pieces = []
    for split in ['train', 'test']:
        frame = pd.read_json(ROOT / f'data/raw/gretel/{split}.jsonl', lines=True)
        frame = frame.rename(columns={'input_text': 'original_text', 'output_text': 'condition'})
        frame['publisher_split'] = split
        frame['source_id'] = [f'gretel-{split}-{i:04d}' for i in range(len(frame))]
        pieces.append(frame)
    all_data = pd.concat(pieces, ignore_index=True)
    all_data['condition'] = all_data.condition.str.strip().str.lower()
    conditions = sorted(all_data.condition.unique().tolist())
    mapping = read_json(ROOT / 'config/specialty_mapping.json')
    assert set(conditions) == set(mapping['mapping']), 'Every source label needs an explicit mapping.'
    all_data['specialty'] = all_data.condition.map(mapping['mapping'])
    all_data['text'] = all_data.original_text.map(lambda x: remove_condition_names(x, conditions))
    all_data['text_sha256'] = all_data.text.map(lambda s: hashlib.sha256(s.encode()).hexdigest())
    original_count = len(all_data)
    conflicting_hashes = all_data.groupby('text_sha256').condition.nunique()
    conflicting_hashes = set(conflicting_hashes[conflicting_hashes > 1].index)
    conflict_count = int(all_data.text_sha256.isin(conflicting_hashes).sum())
    all_data = all_data[~all_data.text_sha256.isin(conflicting_hashes)]
    # Keep publisher test rows over identical training rows. This is a text-only split audit;
    # the classifier vectorizers below are fitted on training text only.
    all_data = all_data.sort_values('publisher_split').drop_duplicates('text_sha256').reset_index(drop=True)
    duplicate_count = original_count - conflict_count - len(all_data)
    audit_features = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5)).fit_transform(all_data.text)
    similarities = (audit_features @ audit_features.T).tocsr()
    similarities.data = (similarities.data >= 0.90).astype(float)
    similarities.eliminate_zeros()
    _, groups = connected_components(similarities, directed=False)
    all_data['group_id'] = groups
    test = all_data[all_data.publisher_split == 'test'].copy()
    pool = all_data[all_data.publisher_split == 'train'].copy()
    excluded = pool[pool.group_id.isin(test.group_id)].copy()
    pool = pool[~pool.group_id.isin(test.group_id)].reset_index(drop=True)
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=SEED)
    for train_idx, val_idx in cv.split(pool.text, pool.condition, pool.group_id):
        train, val = pool.iloc[train_idx].copy(), pool.iloc[val_idx].copy()
        if set(train.condition) == set(conditions) and set(val.condition) == set(conditions):
            break
    else:
        raise RuntimeError('Could not obtain label-complete grouped train/validation partitions.')
    processed = ROOT / 'data/processed'
    processed.mkdir(parents=True, exist_ok=True)
    parts = {'train': train, 'validation': val, 'test': test}
    counts = {}
    for split, frame in parts.items():
        frame.to_csv(processed / f'{split}.csv', index=False)
        counts[split] = {'rows': len(frame), 'groups': int(frame.group_id.nunique()),
                         'conditions': frame.condition.value_counts().to_dict(),
                         'specialties': frame.specialty.value_counts().to_dict()}
    excluded.to_csv(processed / 'excluded_train_near_test.csv', index=False)
    for left, right in [('train', 'validation'), ('train', 'test'), ('validation', 'test')]:
        assert not set(parts[left].group_id) & set(parts[right].group_id)
        assert not set(parts[left].text_sha256) & set(parts[right].text_sha256)
    labels = {'condition': conditions, 'specialty': sorted(all_data.specialty.unique().tolist())}
    write_json(processed / 'labels.json', labels)
    audit = {'source_rows': original_count, 'exact_duplicate_rows_removed': duplicate_count,
             'conflicting_label_rows_removed': conflict_count,
             'training_rows_removed_for_similarity_to_test': len(excluded),
             'near_duplicate_cosine_threshold': 0.90, 'split_counts': counts,
             'label_provenance': mapping['status'],
             'preprocessing': 'Lowercase, normalize apostrophes/whitespace, remove all exact condition names. Keep negations.',
             'limits': 'Text grouping cannot detect every semantic paraphrase. LLM-rewritten source data; no clinical gold-standard routing labels. No external validation.'}
    write_json(ROOT / 'reports/data_audit.json', audit)
    journal('DATA_PREPARED', audit)


if __name__ == '__main__':
    prepare()
