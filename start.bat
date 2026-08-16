@echo off
REM ============================================================
REM  AgriCare - start the app (backend + frontend, one server)
REM  Double-click this file, or run:  start.bat
REM ============================================================
cd /d "%~dp0"

if not exist "venv\Scripts\python.exe" (
    echo.
    echo [!] No virtual environment found.
    echo     Run these once, then start again:
    echo.
    echo       python -m venv venv
    echo       venv\Scripts\activate.bat
    echo       pip install -r backend\requirements.txt
    echo.
    pause
    exit /b 1
)

if "%PORT%"=="" set PORT=5000

echo.
echo  Starting AgriCare on http://localhost:%PORT%
echo  First start takes 40-60 seconds (loading the models)...
echo  Press Ctrl+C to stop.
echo.

"venv\Scripts\python.exe" "backend\app.py"

echo.
echo  Server stopped.
pause
