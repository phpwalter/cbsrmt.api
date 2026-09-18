param(
    [string]$HostName = "127.0.0.1",
    [int]$Port = 8000
)

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
    Write-Host "Created .env from .env.example. Review credentials before production use."
}

& $Python -m uvicorn cbsrmt_api.main:app --host $HostName --port $Port --reload
