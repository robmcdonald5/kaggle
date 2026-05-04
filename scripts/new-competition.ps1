<#
.SYNOPSIS
    Scaffold a new Kaggle competition directory from competitions/_template/.

.DESCRIPTION
    Copies the template, creates the gitignored data/ subdirs, fills in the
    competition slug in README placeholders, and optionally downloads the
    competition data via the Kaggle CLI.

.PARAMETER Slug
    The Kaggle competition slug (the part of the URL after /competitions/).
    Use kebab-case, e.g. "titanic" or "house-prices-advanced-regression".

.PARAMETER Name
    Optional human-readable name for the README. Defaults to a Title-Cased
    version of the slug.

.PARAMETER Download
    If set, runs `kaggle competitions download -c <slug> -p data/raw/` after
    scaffolding. Requires a configured ~/.kaggle/kaggle.json.

.EXAMPLE
    .\scripts\new-competition.ps1 -Slug titanic

.EXAMPLE
    .\scripts\new-competition.ps1 -Slug house-prices-advanced-regression -Download
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidatePattern('^[a-z0-9][a-z0-9-]*$')]
    [string]$Slug,

    [string]$Name,

    [switch]$Download
)

$ErrorActionPreference = 'Stop'

$repoRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
$template = Join-Path $repoRoot 'competitions/_template'
$dest     = Join-Path $repoRoot "competitions/$Slug"

if (-not (Test-Path $template)) {
    throw "Template not found at $template"
}
if (Test-Path $dest) {
    throw "Competition already exists: $dest"
}

if (-not $Name) {
    $Name = ($Slug -split '-' | ForEach-Object {
        $_.Substring(0, 1).ToUpper() + $_.Substring(1)
    }) -join ' '
}

Write-Host "Scaffolding competitions/$Slug ..." -ForegroundColor Cyan
Copy-Item -Recurse -Path $template -Destination $dest

# Local-only data subdirs (gitignored).
$dataDirs = @('data/raw', 'data/interim', 'data/processed')
foreach ($d in $dataDirs) {
    New-Item -ItemType Directory -Force -Path (Join-Path $dest $d) | Out-Null
}

# Fill in the README placeholders.
$readmePath = Join-Path $dest 'README.md'
$readme = Get-Content -Raw -Path $readmePath
$readme = $readme.Replace('{{Competition Name}}', $Name)
$readme = $readme.Replace('{{slug}}', $Slug)
$readme = $readme.Replace('{{YYYY-MM-DD}}', (Get-Date -Format 'yyyy-MM-dd'))
Set-Content -Path $readmePath -Value $readme -NoNewline

Write-Host "Created competitions/$Slug" -ForegroundColor Green

if ($Download) {
    $kaggle = Get-Command kaggle -ErrorAction SilentlyContinue
    if (-not $kaggle) {
        Write-Warning 'kaggle CLI not found on PATH. Run `uv sync` (or `pip install kaggle`) first, then download manually.'
        return
    }
    $rawDir = Join-Path $dest 'data/raw'
    Write-Host "Downloading data to $rawDir ..." -ForegroundColor Cyan
    & kaggle competitions download -c $Slug -p $rawDir
    Get-ChildItem $rawDir -Filter '*.zip' | ForEach-Object {
        Write-Host "Unzipping $($_.Name) ..." -ForegroundColor Cyan
        Expand-Archive -Path $_.FullName -DestinationPath $rawDir -Force
        Remove-Item $_.FullName
    }
    Write-Host 'Data ready.' -ForegroundColor Green
}

Write-Host ''
Write-Host 'Next steps:'
Write-Host "  cd competitions/$Slug"
if (-not $Download) {
    Write-Host "  kaggle competitions download -c $Slug -p data/raw/"
}
Write-Host '  jupyter lab notebooks/'
