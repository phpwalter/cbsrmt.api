param()

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
Set-Location $Root

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    python -m venv .venv
}

$Python = ".venv\Scripts\python.exe"
& $Python -m pip install --disable-pip-version-check -e ".[dev]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Set AUDIO_ROOT before continuing."
    exit 1
}

& $Python -m cbsrmt_api.audio_library
if ($LASTEXITCODE -ne 0) { throw "Audio synchronization failed." }
