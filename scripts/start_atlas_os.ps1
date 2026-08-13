param([switch]$BackgroundOnly)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$atlasUrl = "http://127.0.0.1:8000/app/atlas-opening.html"
$python = Join-Path $env:LOCALAPPDATA "Programs\Python\Python314\python.exe"
$logDirectory = Join-Path $projectRoot "atlas-data\private"

if (-not (Test-Path $python)) {
    $python = (Get-Command py).Source
}

New-Item `
    -ItemType Directory `
    -Path $logDirectory `
    -Force |
    Out-Null

function Test-AtlasProcess {
    param(
        [Parameter(Mandatory)]
        [string]$Pattern
    )

    return [bool](
        Get-CimInstance Win32_Process |
        Where-Object {
            $_.CommandLine -and
            $_.CommandLine -match [regex]::Escape($Pattern)
        } |
        Select-Object -First 1
    )
}

function Start-AtlasPythonProcess {
    param(
        [Parameter(Mandatory)]
        [string]$Script,

        [Parameter(Mandatory)]
        [string]$OutputLog,

        [Parameter(Mandatory)]
        [string]$ErrorLog
    )

    Start-Process `
        -FilePath $python `
        -ArgumentList "-X", "utf8", $Script `
        -WorkingDirectory $projectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput (
            Join-Path $logDirectory $OutputLog
        ) `
        -RedirectStandardError (
            Join-Path $logDirectory $ErrorLog
        )
}

$serverRunning = Get-NetTCPConnection `
    -LocalPort 8000 `
    -State Listen `
    -ErrorAction SilentlyContinue

if (-not $serverRunning) {
    Start-AtlasPythonProcess `
        -Script ".\tools\atlas_web_server.py" `
        -OutputLog "atlas-launch-output.log" `
        -ErrorLog "atlas-launch-error.log"

    Start-Sleep -Seconds 2
}

if (-not (Test-AtlasProcess "watch_atlas_coach_fit.py")) {
    Start-AtlasPythonProcess `
        -Script ".\scripts\watch_atlas_coach_fit.py" `
        -OutputLog "atlas-fit-watcher-output.log" `
        -ErrorLog "atlas-fit-watcher-error.log"
}

if (-not (Test-AtlasProcess "watch_atlas_wellness.py")) {
    Start-AtlasPythonProcess `
        -Script ".\scripts\watch_atlas_wellness.py" `
        -OutputLog "atlas-wellness-watcher-output.log" `
        -ErrorLog "atlas-wellness-watcher-error.log"
}

if (-not $BackgroundOnly) {
    Start-Process $atlasUrl
}