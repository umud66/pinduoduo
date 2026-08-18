param(
    [switch]$SkipInstall
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not $SkipInstall) {
    python -m pip install --upgrade pip
    python -m pip install -e ".[dev]"
}

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    throw "Build requires Node.js/npm because the frontend is Vue 3 + Vite. End users do not need Node.js."
}

Push-Location frontend
try {
    if (Test-Path package-lock.json) { npm ci } else { npm install }
    npm run build
} finally {
    Pop-Location
}

if (-not (Test-Path "app/static/index.html")) {
    throw "Frontend build did not create app/static/index.html"
}

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name "PDD运营助手" `
    --add-data "app/static;app/static" `
    scripts/desktop_entry.py

Write-Host "Build complete: dist/PDD运营助手/"
