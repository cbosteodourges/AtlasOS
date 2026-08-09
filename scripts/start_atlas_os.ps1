$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$atlasUrl = "http://127.0.0.1:8000/app/atlas-opening.html"
$pythonw = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\pythonw.exe"

$serverRunning = Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue

if (-not $serverRunning) {
    if (-not (Test-Path $pythonw)) {
        $pythonw = (Get-Command py).Source
    }

    Start-Process `
        -FilePath $pythonw `
        -ArgumentList "-m", "http.server", "8000", "--bind", "127.0.0.1" `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden

    Start-Sleep -Seconds 2
}

Start-Process $atlasUrl