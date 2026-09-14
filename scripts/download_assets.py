"""Download only public data and safe model weights, pinned to resolved revisions."""
import argparse
import hashlib
import json
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def download(url, target):
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_suffix(target.suffix + '.part')
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=120) as response, temporary.open('wb') as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            temporary.replace(target)
            digest = hashlib.sha256(target.read_bytes()).hexdigest()
            print(f'Downloaded {target.name}: {target.stat().st_size:,} bytes', flush=True)
            return {'file': str(target.relative_to(ROOT)), 'url': url,
                    'bytes': target.stat().st_size, 'sha256': digest}
        except Exception:
            if attempt == 2:
                raise
            time.sleep(2)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=['all', 'data', 'model'], default='all')
    args = parser.parse_args()
    specs = [
        ('data', 'datasets/gretelai/symptom_to_diagnosis', 'gretelai/symptom_to_diagnosis',
         ROOT / 'data/raw/gretel', ['README.md', 'train.jsonl', 'test.jsonl']),
        ('model', 'distilbert/distilbert-base-uncased', 'distilbert/distilbert-base-uncased',
         ROOT / 'models/pretrained/distilbert',
         ['README.md', 'LICENSE', 'config.json', 'tokenizer_config.json', 'tokenizer.json',
          'vocab.txt', 'model.safetensors']),
    ]
    for kind, path, repo, folder, files in specs:
        if args.only not in ('all', kind):
            continue
        api_path = f'datasets/{repo}' if kind == 'data' else f'models/{repo}'
        metadata = get_json('https://huggingface.co/api/' + api_path)
        revision = metadata['sha']
        manifest_path = folder / 'download_manifest.json'
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding='utf-8'))
            if previous['revision'] == revision and all(
                (ROOT / entry['file']).exists() and
                hashlib.sha256((ROOT / entry['file']).read_bytes()).hexdigest() == entry['sha256']
                for entry in previous['files']
            ):
                print(f'Already verified: {repo} @ {revision}', flush=True)
                continue
        entries = [download(f'https://huggingface.co/{path}/resolve/{revision}/{name}', folder / name)
                   for name in files]
        manifest = {'repo': repo, 'revision': revision, 'license_declared_by_publisher':
                    metadata.get('cardData', {}).get('license', 'see model/dataset card'),
                    'downloaded_at_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
                    'files': entries}
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
