@echo off
REM Start Backend Server

echo.
echo ============================================================
echo    Starting Multi-Agent Backend Server
echo ============================================================
echo.

cd /d "%~dp0\..\src\backend"

if not exist ".env" (
    echo WARNING: .env file not found!
    echo Backend may not start correctly without environment variables.
    echo.
    set /p continue="Continue anyway? (y/n): "
    if /i not "%continue%"=="y" (
        echo Aborted.
        exit /b 1
    )
)

echo.
echo Starting uvicorn server...
echo   URL: http://localhost:8000
echo   Docs: http://localhost:8000/docs
echo.
echo Press Ctrl+C to stop the server
echo.

uvicorn app_kernel:app --reload --port 8000

if errorlevel 1 (
    echo.
    echo ERROR: Failed to start backend server!
    echo.
    echo Make sure uvicorn is installed:
    echo   pip install uvicorn
    echo.
    pause
    exit /b 1
)

