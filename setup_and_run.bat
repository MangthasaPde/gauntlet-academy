@echo off
setlocal
cd /d "%~dp0"
set PYTHONUTF8=1
if "%GAUNTLET_PORT%"=="" set GAUNTLET_PORT=8000
if "%GAUNTLET_PYTHON%"=="" (set "PYTHON=py -3") else (set "PYTHON=%GAUNTLET_PYTHON%")
%PYTHON% -c "import sys; assert sys.version_info >= (3,11), 'Python 3.11+ is required; Python 3.12 recommended'"
if errorlevel 1 (
  echo Install Python 3.11 or 3.12 from python.org ^(tick "Add python.exe to PATH"^), then rerun this file.
  pause
  exit /b 1
)
if not exist .venv\Scripts\python.exe %PYTHON% -m venv .venv
call .venv\Scripts\activate.bat
fc /b requirements.txt .venv\.requirements-installed >nul 2>&1
if errorlevel 1 (
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt || (pause & exit /b 1)
  copy /y requirements.txt .venv\.requirements-installed >nul
)
if not exist workspace mkdir workspace
if not exist data mkdir data
if not exist .env copy .env.example .env >nul
echo.
echo GAUNTLET ACADEMY
echo Open http://localhost:%GAUNTLET_PORT%  ^|  Ctrl+C to stop
echo Edit quest files inside %CD%\workspace
echo Verification runs your Python as your Windows user. Run only code you trust.
echo.
python -m uvicorn app.main:app --host 127.0.0.1 --port %GAUNTLET_PORT%
