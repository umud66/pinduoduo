@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] 未检测到 Python 3.11+。
  echo 正式发布版无需 Python；源码开发请先安装 Python。
  pause
  exit /b 1
)
where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Vue 源码开发需要 Node.js/npm。
  echo 普通用户请使用 GitHub Release 中的 Windows 发布包，无需安装 Node.js。
  pause
  exit /b 1
)

if not exist .venv py -3 -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -q -e .
if errorlevel 1 exit /b 1
python scripts\dev.py
