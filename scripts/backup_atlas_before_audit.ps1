# Sauvegarde privee. Aucun git pull, reset, nettoyage ou envoi reseau.
[CmdletBinding()]
param(
    [string]$ProjectPath = (Join-Path $env:USERPROFILE 'OneDrive\Documents\GitHub\AtlasOS'),
    [string]$BackupRoot = (Join-Path $env:LOCALAPPDATA 'AtlasOS-Backups'),
    [string[]]$ExtraPath = @(),
    [Parameter(Mandatory = $true)][string[]]$BrowserExport
)
$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

function Get-AtlasManifest([string]$Directory) {
    $prefix = $Directory.TrimEnd('\') + '\'
    $result = @{}
    foreach ($file in (Get-ChildItem -LiteralPath $Directory -File -Recurse -Force -ErrorAction Stop)) {
        $relative = $file.FullName.Substring($prefix.Length)
        $result[$relative] = (Get-FileHash -LiteralPath $file.FullName -Algorithm SHA256).Hash
    }
    return $result
}
function Assert-AtlasManifest($Expected, $Actual, [string]$Label) {
    if ($Expected.Count -ne $Actual.Count) { throw "Nombre de fichiers different : $Label" }
    foreach ($key in $Expected.Keys) {
        if (-not $Actual.ContainsKey($key) -or $Expected[$key] -ne $Actual[$key]) {
            throw "Fichier modifie ou illisible : $Label. Sauvegarde NON VALIDEE."
        }
    }
}

$project = (Resolve-Path -LiteralPath $ProjectPath).Path.TrimEnd('\')
if (-not (Test-Path -LiteralPath (Join-Path $project '.git') -PathType Container)) {
    throw 'Un depot Git standard est requis. Worktree externe : procedure specifique necessaire.'
}
$branch = (& git -C $project branch --show-current).Trim()
if ($LASTEXITCODE -ne 0 -or $branch -ne 'health-connect-auto-sync') {
    throw "Branche inattendue : $branch. Aucune branche n'a ete changee."
}
$sha = (& git -C $project rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Impossible de lire le commit.' }

# Les lanceurs habituels utilisent des chemins relatifs : on refuse toute
# instance Atlas de cette session plutot que risquer de manquer un redacteur.
$writers = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^(python(?:w)?(?:3(?:\.\d+)?)?|py)\.exe$' -and
    $_.CommandLine -match '(atlas_web_server|watch_atlas_coach_fit|watch_atlas_wellness|sync_atlas_coach_pilot)\.py'
})
if ($writers.Count) {
    $ids = ($writers | ForEach-Object { $_.ProcessId }) -join ', '
    throw "Atlas ecrit peut-etre encore. Ferme les processus Atlas PID $ids, puis relance. Aucun processus n'a ete arrete."
}
if ($BrowserExport.Count -eq 0) { throw 'Au moins un export du navigateur Atlas est requis.' }
$exports = @()
foreach ($path in $BrowserExport) {
    $resolved = (Resolve-Path -LiteralPath $path).Path
    $data = Get-Content -LiteralPath $resolved -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($data.schema -ne 'atlas-local-backup-v1' -or -not $data.origin -or $null -eq $data.storage) {
        throw 'Export navigateur invalide. Utilise la procedure du document de sauvegarde.'
    }
    $exports += $resolved
}

$backupBase = [IO.Path]::GetFullPath($BackupRoot).TrimEnd('\')
$sources = @($project)
foreach ($extra in $ExtraPath) {
    $item = Get-Item -LiteralPath $extra
    if (-not $item.PSIsContainer) { throw 'ExtraPath attend des dossiers.' }
    $sources += $item.FullName.TrimEnd('\')
}
foreach ($source in $sources) {
    if ($backupBase.Equals($source, [StringComparison]::OrdinalIgnoreCase) -or
        $backupBase.StartsWith($source + '\', [StringComparison]::OrdinalIgnoreCase)) {
        throw 'La destination ne doit pas etre dans un dossier a sauvegarder.'
    }
    $links = @(Get-ChildItem -LiteralPath $source -Recurse -Force | Where-Object {
        $_.LinkType -eq 'Junction' -or $_.LinkType -eq 'SymbolicLink'
    })
    if ($links.Count) { throw 'Liens symboliques/jonctions presents : inventorier leurs cibles avant de copier.' }
}
$stamp = [DateTime]::UtcNow.ToString('yyyyMMdd-HHmmss-fff')
$destination = Join-Path $backupBase ("avant-audit-$stamp-" + $sha.Substring(0, 7))
New-Item -ItemType Directory -Path $destination | Out-Null
# Retire les acces herites, conserve seulement l'utilisateur courant et SYSTEM.
$sid = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
& icacls.exe $destination '/inheritance:r' '/grant:r' "*$($sid):(OI)(CI)F" '*S-1-5-18:(OI)(CI)F' | Out-Null
if ($LASTEXITCODE -ne 0) { throw 'Impossible de restreindre les droits de la sauvegarde.' }

$inventory = @()
for ($i = 0; $i -lt $sources.Count; $i++) {
    $source = $sources[$i]
    $name = if ($i -eq 0) { 'AtlasOS' } else { "externe-$i" }
    $target = Join-Path $destination $name
    Write-Host "Lecture et verification SHA-256 : $name (peut prendre plusieurs minutes)..."
    $before = Get-AtlasManifest $source
    & robocopy.exe $source $target /E /COPY:DAT /DCOPY:DAT /R:1 /W:1 /XJ /NFL /NDL /NP /NJH /NJS
    if ($LASTEXITCODE -ge 8) { throw "Copie incomplete : $name. Sauvegarde NON VALIDEE." }
    $after = Get-AtlasManifest $source
    $copy = Get-AtlasManifest $target
    Assert-AtlasManifest $before $after "source $name"
    Assert-AtlasManifest $before $copy "copie $name"
    $inventory += [ordered]@{ source = $source; folder = $name; files = $copy.Count; sha256 = $copy }
}
$browserDirectory = Join-Path $destination 'navigateurs'
New-Item -ItemType Directory -Path $browserDirectory | Out-Null
for ($i = 0; $i -lt $exports.Count; $i++) {
    $target = Join-Path $browserDirectory "atlas-navigateur-$i.json"
    Copy-Item -LiteralPath $exports[$i] -Destination $target
    if ((Get-FileHash -LiteralPath $exports[$i]).Hash -ne (Get-FileHash -LiteralPath $target).Hash) {
        throw 'Export navigateur mal copie.'
    }
}
$repoCopy = Join-Path $destination 'AtlasOS'
$copySha = (& git -C $repoCopy rev-parse HEAD).Trim()
if ($LASTEXITCODE -ne 0 -or $copySha -ne $sha) { throw 'Commit de la copie non conforme.' }
& git -C $repoCopy fsck --full
if ($LASTEXITCODE -ne 0) { throw 'Verification des objets Git en echec.' }
$manifest = [ordered]@{
    schema = 'atlas-private-backup-v1'; utc = [DateTime]::UtcNow.ToString('o');
    commit = $sha; branch = $branch; directories = $inventory;
    browser_export_count = $exports.Count;
    limitations = @('Pas de sauvegarde Android native, ni de Health Connect.',
        'Les origines et appareils non exportes restent hors couverture.',
        'Les dossiers externes non fournis restent hors couverture.',
        'Restauration applicative Windows non testee par ce script.')
}
$manifest | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $destination 'manifest-private.json') -Encoding UTF8
@("Commit : $sha", "Branche : $branch", "Fichiers copies et SHA-256 verifies.",
  "Exports navigateurs : $($exports.Count)", 'Ne pas envoyer cette sauvegarde a GitHub ou dans une conversation.') |
    Set-Content -LiteralPath (Join-Path $destination 'SAUVEGARDE-VERIFIEE.txt') -Encoding UTF8
Write-Host "Sauvegarde privee verifiee : $destination" -ForegroundColor Green
Write-Host 'Communique seulement : sauvegarde OK, nombre de navigateurs exportes et eventuels dossiers manquants.'
