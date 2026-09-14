$ErrorActionPreference = 'Stop'
$taskReportUrl = 'http://127.0.0.1:8766/dashboard/index.html'
$taskReady = $false
try {
    $taskResponse = Invoke-WebRequest -Uri $taskReportUrl -TimeoutSec 3
    $taskReady = $taskResponse.Content.Contains('Healthcare AI')
} catch { }
if (-not $taskReady) {
    $taskListener = Get-NetTCPConnection -LocalPort 8766 -State Listen -ErrorAction SilentlyContinue
    if ($taskListener) { throw 'Port 8766 is occupied by another service. Open reports\dashboard\index.html directly.' }
    $taskPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    $taskDirectory = Join-Path $PSScriptRoot 'reports'
    $taskLogDir = Join-Path $PSScriptRoot 'logs'
    $taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-m','http.server','8766','--bind','127.0.0.1','--directory',('"' + $taskDirectory + '"')) -WorkingDirectory $PSScriptRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $taskLogDir 'report_server_stdout.log') -RedirectStandardError (Join-Path $taskLogDir 'report_server_stderr.log') -PassThru
    $taskProcess.Id | Set-Content -LiteralPath (Join-Path $taskLogDir 'report_server.pid')
    for ($taskAttempt = 0; $taskAttempt -lt 20; $taskAttempt++) {
        Start-Sleep -Milliseconds 250
        try {
            $taskResponse = Invoke-WebRequest -Uri $taskReportUrl -TimeoutSec 2
            if ($taskResponse.Content.Contains('Healthcare AI')) { $taskReady = $true; break }
        } catch { }
    }
}
if (-not $taskReady) { throw 'Report server did not start. See logs\report_server_stderr.log.' }
Start-Process -FilePath $taskReportUrl
Write-Output $taskReportUrl
