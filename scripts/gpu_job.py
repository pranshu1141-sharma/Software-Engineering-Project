"""Durable local background job: resume CUDA download, install, train and verify."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import traceback

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from healthcare_ml.common import journal, write_json


def status(state, phase, **extra):
    value = {'state': state, 'phase': phase, 'updated_at_utc': datetime.now(timezone.utc).isoformat(),
             'worker_pid': os.getpid(), **extra}
    write_json(ROOT / 'reports/gpu_job_status.json', value)
    (ROOT / 'GPU_JOB_STATUS.txt').write_text(
        '\n'.join(f'{k}: {v}' for k, v in value.items()) + '\n\nLog: logs/gpu_job.log\n', encoding='utf-8')


def run(phase, args, log):
    status('running', phase)
    journal('BACKGROUND_STAGE_STARTED', {'phase': phase})
    env = dict(os.environ, HF_HUB_DISABLE_TELEMETRY='1', TOKENIZERS_PARALLELISM='false',
               PYTHONUNBUFFERED='1', PYTHONUTF8='1')
    process = subprocess.Popen([sys.executable, *args], cwd=ROOT, env=env,
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                               encoding='utf-8', errors='replace', creationflags=subprocess.CREATE_NO_WINDOW)
    status('running', phase, child_pid=process.pid)
    for line in process.stdout:
        log.write(line)
        log.flush()
        if line.strip():
            status('running', phase, child_pid=process.pid, latest_message=line.strip()[-700:])
    code = process.wait()
    if code:
        raise RuntimeError(f'{phase} failed with exit code {code}; see logs/gpu_job.log')
    journal('BACKGROUND_STAGE_COMPLETED', {'phase': phase})


def main():
    (ROOT / 'logs').mkdir(exist_ok=True)
    lock = ROOT / '.cache/gpu_job.lock'
    lock.parent.mkdir(exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('A job lock already exists. Inspect its process before restarting.')
    os.write(fd, str(os.getpid()).encode())
    os.close(fd)
    try:
        with (ROOT / 'logs/gpu_job.log').open('a', encoding='utf-8') as log:
            journal('BACKGROUND_JOB_STARTED', {'pid': os.getpid(), 'scope': 'CUDA setup, DistilBERT training, summary, plots, tests'})
            run('download_cuda_wheel', ['scripts/download_cuda_wheel.py'], log)
            run('install_cuda_torch', ['-m', 'pip', 'install', '--no-cache-dir',
                                      '.cache/torch-2.7.1+cu126-cp312-cp312-win_amd64.whl'], log)
            run('install_accelerate', ['-m', 'pip', 'install', 'accelerate>=1,<2'], log)
            run('verify_cuda', ['-c', "import torch; assert torch.cuda.is_available(), 'CUDA unavailable'; print(torch.__version__,torch.cuda.get_device_name(0))"], log)
            run('train_distilbert', ['-m', 'healthcare_ml.train_transformer', '--epochs', '4'], log)
            run('summarize_results', ['scripts/summarize.py'], log)
            run('plot_results', ['scripts/plot_results.py'], log)
            run('verify_all_models', ['-m', 'pytest', '-q'], log)
            frozen = subprocess.check_output([sys.executable, '-m', 'pip', 'list', '--format=freeze'], cwd=ROOT, text=True)
            (ROOT / 'requirements-lock.txt').write_text(frozen, encoding='utf-8')
            journal('BACKGROUND_JOB_COMPLETED', {'verification': 'All model tests passed', 'results': 'reports/RUN_SUMMARY.txt'})
            status('completed', 'all_models_trained_and_verified')
    except BaseException as error:
        status('failed', 'see_log', error=str(error))
        journal('BACKGROUND_JOB_FAILED', {'error': str(error), 'log': 'logs/gpu_job.log'})
        traceback.print_exc()
        raise
    finally:
        lock.unlink(missing_ok=True)


if __name__ == '__main__':
    main()
