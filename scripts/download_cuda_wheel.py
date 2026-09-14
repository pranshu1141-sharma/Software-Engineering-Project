"""Range-download official CUDA wheel when a single large transfer stalls.

The final SHA256 is taken from the official PyTorch wheel index and checked
before this file can be installed. No package installation occurs here.
"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
URL = 'https://download.pytorch.org/whl/cu126/torch-2.7.1%2Bcu126-cp312-cp312-win_amd64.whl'
EXPECTED = '7d897b5ff67e778de4a2a05d4528377003105e29854fd73ecbe965287533f08b'
SIZE = 2716918001
CHUNK = 16 * 1024 * 1024
FOLDER = ROOT / '.cache/cuda_download'


def fetch(start):
    end = min(start + CHUNK, SIZE) - 1
    path = FOLDER / f'{start:012d}.part'
    if path.exists() and path.stat().st_size == end - start + 1:
        return path
    for attempt in range(4):
        try:
            request = urllib.request.Request(URL + f'?range_start={start}',
                                             headers={'Range': f'bytes={start}-{end}'})
            with urllib.request.urlopen(request, timeout=90) as response:
                assert response.status == 206
                assert response.headers['Content-Range'] == f'bytes {start}-{end}/{SIZE}'
                data = response.read()
                assert len(data) == end - start + 1
            path.write_bytes(data)
            return path
        except Exception:
            if attempt == 3:
                raise
            time.sleep(2)


def main():
    FOLDER.mkdir(parents=True, exist_ok=True)
    starts = list(range(0, SIZE, CHUNK))
    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(fetch, start) for start in starts]
        for count, future in enumerate(as_completed(futures), 1):
            future.result()
            if count % 8 == 0 or count == len(starts):
                print(f'CUDA wheel download: {count}/{len(starts)} chunks', flush=True)
    destination = ROOT / '.cache/torch-2.7.1+cu126-cp312-cp312-win_amd64.whl'
    digest = hashlib.sha256()
    with destination.open('wb') as output:
        for start in starts:
            data = (FOLDER / f'{start:012d}.part').read_bytes()
            digest.update(data)
            output.write(data)
    if digest.hexdigest() != EXPECTED:
        raise RuntimeError('Official wheel SHA256 verification failed; do not install.')
    print(f'Official SHA256 verified: {digest.hexdigest()}\n{destination}', flush=True)


if __name__ == '__main__':
    main()
