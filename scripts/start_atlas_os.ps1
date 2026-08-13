$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$atlasUrl = "http://127.0.0.1:8000/app/atlas-opening.html"
$pythonw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"

$serverRunning = Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue

if (-not $serverRunning) {
    if (-not (Test-Path $pythonw)) {
        $pythonw = (Get-Command py).Source
    }

    $logDirectory = Join-Path $projectRoot "atlas-data\private"
    New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null

    Start-Process `
        -FilePath $pythonw `
        -ArgumentList "-X", "utf8", ".\tools\atlas_web_server.py" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logDirectory "atlas-launch-output.log") `
        -RedirectStandardError (Join-Path $logDirectory "atlas-launch-error.log")

    Start-Sleep -Seconds 2
}

Start-Process $atlasUrl