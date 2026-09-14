param([switch]$SkipTransformer)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$env:HF_HUB_OFFLINE = '1'
$env:HF_HUB_DISABLE_TELEMETRY = '1'
$env:TOKENIZERS_PARALLELISM = 'false'
& .\.venv\Scripts\python.exe -m healthcare_ml.prepare
if ($LASTEXITCODE -ne 0) { throw 'Data preparation failed.' }
& .\.venv\Scripts\python.exe -m healthcare_ml.train_baseline
if ($LASTEXITCODE -ne 0) { throw 'Baseline training failed.' }
& .\.venv\Scripts\python.exe -m healthcare_ml.train_queue
if ($LASTEXITCODE -ne 0) { throw 'Queue training failed.' }
if (-not $SkipTransformer) {
    & .\.venv\Scripts\python.exe -m healthcare_ml.train_transformer --epochs 4
    if ($LASTEXITCODE -ne 0) { throw 'Transformer training failed.' }
}
& .\.venv\Scripts\python.exe scripts\summarize.py
if ($LASTEXITCODE -ne 0) { throw 'Summary generation failed.' }
