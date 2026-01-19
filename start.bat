@echo off
echo.
echo ==========================================
echo    News Summarizer Agent - Starting...
echo ==========================================
echo.

:: Check if venv exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found.
    echo Please create it first with: python -m venv venv
    echo Then activate and install requirements.
    pause
    exit /b 1
)

:: Check if frontend node_modules exists
if not exist "frontend\node_modules" (
    echo Installing frontend dependencies...
    cd frontend
    call npm install
    cd ..
)

:: Start backend in new window (run from project root for proper imports)
echo Starting FastAPI backend on http://localhost:8000
start "News Summarizer - Backend" cmd /k "cd /d %~dp0 && venv\Scripts\activate && python -m uvicorn backend.main:app --reload --port 8000"

:: Wait a moment for backend to start
timeout /t 3 /nobreak > nul

:: Start frontend in new window
echo Starting React frontend on http://localhost:5173
start "News Summarizer - Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Wait a moment for frontend to start
timeout /t 3 /nobreak > nul

:: Open browser
echo Opening browser...
start http://localhost:5173

echo.
echo ==========================================
echo    Application is running!
echo ==========================================
echo.
echo    Frontend: http://localhost:5173
echo    Backend:  http://localhost:8000
echo    API Docs: http://localhost:8000/docs
echo.
echo    Close this window to keep servers running
echo    Or press any key to exit this window
echo.
pause > nul
