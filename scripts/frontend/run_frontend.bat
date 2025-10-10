@echo off
REM Frontend Development Server Launcher
REM Sprint 4 - Analytics Dashboard

echo ========================================
echo Starting Frontend Development Server
echo ========================================
echo.

cd src\frontend

echo Installing dependencies (if needed)...
call npm install

echo.
echo Starting Vite development server...
echo.
echo Once started, visit:
echo   - Home: http://localhost:5173/
echo   - Analytics Dashboard: http://localhost:5173/analytics
echo.
echo Press Ctrl+C to stop the server
echo.

call npm run dev

