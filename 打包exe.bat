@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"
title First EXE Builder

set "PY=venv\Scripts\python.exe"
set "PIP_INDEX=https://pypi.tuna.tsinghua.edu.cn/simple"
set "WORKER_EXE=build\worker_dist\extract_worker.exe"

echo.
echo  [First] Build started.
echo.

if not exist "%PY%" (
    echo  [INFO] Creating virtual environment: venv
    where py >nul 2>nul
    if not errorlevel 1 (
        py -3 -m venv venv
    ) else (
        python -m venv venv
    )
    if errorlevel 1 goto :fail
)

if not exist "%PY%" (
    echo  [ERROR] Python executable not found: %PY%
    goto :fail
)

if not exist "gui.py" (
    echo  [ERROR] gui.py not found. Please run this script from the project root.
    goto :fail
)

if not exist "src\extract_worker.py" (
    echo  [ERROR] src\extract_worker.py not found.
    goto :fail
)

echo  [1/4] Installing project dependencies...
"%PY%" -m pip install -r requirements.txt -i "%PIP_INDEX%"
if errorlevel 1 goto :fail

echo.
echo  [2/4] Installing PyInstaller...
"%PY%" -m pip install pyinstaller -i "%PIP_INDEX%"
if errorlevel 1 goto :fail

echo.
echo  [3/4] Building extract worker...
"%PY%" -m PyInstaller src\extract_worker.py ^
    --name extract_worker ^
    --onefile ^
    --console ^
    --noconfirm ^
    --clean ^
    --distpath build\worker_dist ^
    --workpath build\worker_build ^
    --specpath build\spec
if errorlevel 1 goto :fail

if not exist "%WORKER_EXE%" (
    echo  [ERROR] Worker build output not found: %WORKER_EXE%
    goto :fail
)

echo.
echo  [4/4] Building First GUI...
"%PY%" -m PyInstaller gui.py ^
    --name First ^
    --windowed ^
    --icon icon.ico ^
    --noconfirm ^
    --clean ^
    --contents-directory . ^
    --add-data "frida;frida" ^
    --add-data "hook_scripts;hook_scripts" ^
    --add-data "src\cloud_audit_inject.js;src" ^
    --add-data "src\nav_inject.js;src" ^
    --add-data "icon.png;." ^
    --add-data "icon.ico;." ^
    --add-binary "%WORKER_EXE%;src"
if errorlevel 1 goto :fail

if not exist "dist\First\First.exe" (
    echo  [ERROR] GUI build output not found: dist\First\First.exe
    goto :fail
)

echo.
echo  [OK] Build finished.
echo  Output: dist\First\First.exe
echo.
pause
exit /b 0

:fail
echo.
echo  [FAILED] Build failed. Check the error above.
echo.
pause
exit /b 1
