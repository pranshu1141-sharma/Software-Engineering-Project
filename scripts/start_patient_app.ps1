param([switch]$NoBrowser)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path $PSScriptRoot -Parent
$appRoot = Join-Path $projectRoot 'patient-app'
$pythonExe = Join-Path $projectRoot '.venv\Scripts\python.exe'
$nodeExe = (Get-Command node.exe -ErrorAction SilentlyContinue).Source
if (-not $nodeExe) { $nodeExe = Join-Path $env:USERPROFILE '.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe' }
if (-not (Test-Path -LiteralPath $pythonExe)) { throw 'The healthcare Python environment is missing. See APP_README.md.' }
if (-not (Test-Path -LiteralPath $nodeExe)) { throw 'Install Node.js 22.13 or newer, then reopen this launcher.' }
if (-not (Test-Path -LiteralPath (Join-Path $appRoot 'node_modules\expo\bin\cli'))) { throw 'App packages are missing. Run npm install in patient-app first.' }
$logRoot = Join-Path $projectRoot 'logs'
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null
function Test-Api {
  try { return (Invoke-RestMethod 'http://127.0.0.1:8001/health' -TimeoutSec 2).app -eq 'carelane-demo' } catch { return $false }
}
function Test-App {
  try { return (Invoke-WebRequest 'http://localhost:8081' -UseBasicParsing -TimeoutSec 2).Content -match '<title>Carelane</title>' } catch { return $false }
}
if (-not (Test-Api)) {
  Write-Host 'Starting the local model and appointment service...'
  Start-Process -FilePath $pythonExe -ArgumentList '-m uvicorn healthcare_ml.patient_api:app --host 127.0.0.1 --port 8001' -WorkingDirectory $projectRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'patient-api.log') -RedirectStandardError (Join-Path $logRoot 'patient-api-error.log') | Out-Null
}
if (-not (Test-App)) {
  Write-Host 'Starting Carelane... First launch may take a minute.'
  $env:EXPO_NO_TELEMETRY = '1'
  $env:CI = $null
  $env:EXPO_PUBLIC_API_URL = 'http://127.0.0.1:8001'
  Start-Process -FilePath $nodeExe -ArgumentList 'node_modules/expo/bin/cli start --web --port 8081 --localhost' -WorkingDirectory $appRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $logRoot 'patient-app.log') -RedirectStandardError (Join-Path $logRoot 'patient-app-error.log') | Out-Null
}
$ready = $false
for ($attempt = 0; $attempt -lt 45; $attempt++) {
  if ((Test-Api) -and (Test-App)) { $ready = $true; break }
  Start-Sleep -Seconds 1
}
if (-not $ready) { throw "Startup did not finish. Check $logRoot\patient-app-error.log and patient-api-error.log. Ports 8001 and 8081 must be free." }
Write-Host 'Carelane is ready: http://localhost:8081'
Write-Host "Saved visits: $projectRoot\data\app_demo.sqlite3"
Write-Host "App and service logs: $logRoot"
if (-not $NoBrowser) { Start-Process 'http://localhost:8081' }
