import hashlib
import importlib.metadata
import json
from datetime import datetime, timezone
from pathlib import Path
import platform
import re
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SEED = 42


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def journal(event, details):
    record = {'at_utc': datetime.now(timezone.utc).isoformat(), 'event': event, **details}
    (ROOT / 'reports').mkdir(exist_ok=True)
    with (ROOT / 'reports/events.jsonl').open('a', encoding='utf-8') as output:
        output.write(json.dumps(record, ensure_ascii=False) + '\n')
    with (ROOT / 'TRAINING_JOURNAL.txt').open('a', encoding='utf-8') as output:
        output.write('\n' + '=' * 72 + '\n' + record['at_utc'] + ' | ' + event + '\n')
        output.write(json.dumps(details, indent=2, ensure_ascii=False) + '\n')
    print(event + ': ' + json.dumps(details, ensure_ascii=False), flush=True)


def source_hashes():
    return {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for folder in ['healthcare_ml', 'scripts', 'config']
            for p in (ROOT / folder).rglob('*') if p.suffix in ['.py', '.json']}


def environment():
    packages = {}
    for name in ['numpy', 'pandas', 'scikit-learn', 'catboost', 'torch', 'transformers',
                 'accelerate', 'fastapi', 'safetensors']:
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            pass
    gpu = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total,driver_version',
                          '--format=csv,noheader'], capture_output=True, text=True)
    return {'python': platform.python_version(), 'platform': platform.platform(),
            'packages': packages, 'gpu': gpu.stdout.strip(), 'seed': SEED}


def normalize(text):
    return re.sub(r'\s+', ' ', str(text).lower().replace('\u2019', "'")).strip()


def remove_condition_names(text, conditions):
    text = normalize(text)
    for condition in sorted(conditions, key=len, reverse=True):
        text = re.sub(r'\b' + re.escape(condition) + r'\b', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()
