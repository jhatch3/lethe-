# Lethe coordinator startup — venv, deps, preflight, uvicorn.
# Run from repo root:  .\tools\start.ps1
#
# Skips pip install if requirements.txt hasn't changed since the last run
# (uses .venv/.requirements.stamp). Pass -ForceInstall to override.

[CmdletBinding()]
param(
    [switch]$ForceInstall,
    [switch]$SkipPreflight,
    [switch]$Strict,
    [int]$Port = 8000
)

$ErrorActionPreference = 'Stop'

$RepoRoot       = Resolve-Path (Join-Path $PSScriptRoot '..')
$Coordinator    = Join-Path $RepoRoot 'src\coordinator'
$Venv           = Join-Path $Coordinator '.venv'
$Activate       = Join-Path $Venv 'Scripts\Activate.ps1'
$Requirements   = Join-Path $Coordinator 'requirements.txt'
$Stamp          = Join-Path $Venv '.requirements.stamp'
$Preflight      = Join-Path $RepoRoot 'tools\preflight.py'

function Write-Step($msg) { Write-Host "==> $msg" -ForegroundColor Cyan }
function Write-Done($msg) { Write-Host "    $msg" -ForegroundColor DarkGray }

# 1. venv
Write-Step "Virtual environment"
if (-not (Test-Path $Activate)) {
    Write-Done "creating $Venv"
    & python -m venv $Venv
    if ($LASTEXITCODE -ne 0) { throw "python -m venv failed" }
} else {
    Write-Done "exists"
}
. $Activate

# 2. requirements
Write-Step "Dependencies"
$needsInstall = $ForceInstall -or -not (Test-Path $Stamp)
if (-not $needsInstall) {
    $reqTime  = (Get-Item $Requirements).LastWriteTimeUtc
    $stampTime = (Get-Item $Stamp).LastWriteTimeUtc
    if ($reqTime -gt $stampTime) { $needsInstall = $true }
}
if ($needsInstall) {
    Write-Done "installing from $Requirements"
    & python -m pip install --disable-pip-version-check -q -r $Requirements
    if ($LASTEXITCODE -ne 0) { throw "pip install failed" }
    Set-Content -Path $Stamp -Value (Get-Date).ToString('o')
} else {
    Write-Done "up to date (use -ForceInstall to override)"
}

# 3. preflight
if (-not $SkipPreflight) {
    Write-Step "Preflight checks"
    $args = @($Preflight)
    if ($Strict) { $args += '--strict' }
    & python @args
    if ($LASTEXITCODE -ne 0 -and $Strict) { throw "preflight failed (strict mode)" }
}

# 4. uvicorn
Write-Step "Starting coordinator on :$Port"
Set-Location $Coordinator
& python -m uvicorn main:app --reload --port $Port