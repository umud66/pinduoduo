#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

skip_install=false
if [[ "${1:-}" == "--skip-install" ]]; then
  skip_install=true
fi

if [[ "$skip_install" != true ]]; then
  python -m pip install --upgrade pip
  python -m pip install -e ".[dev]"
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "Build requires Node.js/npm because the frontend is Vue 3 + Vite. End users do not need Node.js." >&2
  exit 1
fi

pushd frontend >/dev/null
if [[ -f package-lock.json ]]; then
  npm ci --no-audit --no-fund
else
  npm install --no-audit --no-fund
fi
npm run build
popd >/dev/null

if [[ ! -f "app/static/index.html" ]]; then
  echo "Frontend build did not create app/static/index.html" >&2
  exit 1
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
  python -m PyInstaller \
    --noconfirm \
    --clean \
    --onedir \
    --windowed \
    --name "PDD运营助手" \
    --osx-bundle-identifier "com.umud.pdd-ai-operator" \
    --add-data "app/static:app/static" \
    scripts/desktop_entry.py

  test -d "dist/PDD运营助手.app"
  echo "Build complete: dist/PDD运营助手.app"
else
  python -m PyInstaller \
    --noconfirm \
    --clean \
    --onedir \
    --name "PDD-AI-Operator" \
    --add-data "app/static:app/static" \
    scripts/desktop_entry.py

  test -d "dist/PDD-AI-Operator"
  echo "Build complete: dist/PDD-AI-Operator/"
fi
