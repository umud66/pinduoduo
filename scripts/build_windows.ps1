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

python -m PyInstaller `
    --noconfirm `
    --clean `
    --onedir `
    --name "PDD运营助手" `
    --add-data "app/static;app/static" `
    scripts/desktop_entry.py

Write-Host "Build complete: dist/PDD运营助手/"
