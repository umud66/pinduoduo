@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Python 3.11+。
  echo 正式发布版会提供无需 Python 的 exe；源码运行请先安装 Python。
  pause
  exit /b 1
)

if not exist .venv (
  echo [1/3] 正在创建本地运行环境...
  py -3 -m venv .venv
)

call .venv\Scripts\activate.bat

echo [2/3] 正在检查依赖...
python -m pip install -q -e .
if errorlevel 1 (
  echo [ERROR] 依赖安装失败，请检查网络。
  pause
  exit /b 1
)

echo [3/3] 正在启动拼多多 AI 运营助手...
python scripts\dev.py
