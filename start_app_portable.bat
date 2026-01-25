@echo off
set "BACKEND_PORT=8000"

:MENU
cls
echo ===================================================
echo           LetakMaster Portable Launcher
echo ===================================================
echo [1] Start Application (No Install Needed)
echo [2] Stop Application
echo [3] Exit
echo ===================================================
set /p choice=Enter selection: 

if "%choice%"=="1" goto START_APP
if "%choice%"=="2" goto STOP_APP
if "%choice%"=="3" exit
goto MENU

:START_APP
echo.
echo Stopping any existing instances...
call :STOP_APP_SILENT

echo.
echo Starting Backend & GUI (Standard Mode)...
echo The application will be available at http://localhost:%BACKEND_PORT%
echo.
:: Start Uvicorn. Since 'frontend_static' is populated, it serves the UI at root (/).
start "LetakMaster App" cmd /c ".\python_embed\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT%"

echo Launching Browser...
timeout /t 2 >nul
start http://localhost:%BACKEND_PORT%

echo Application is running. Close this window to stop, or use option [2].
pause
goto MENU

:STOP_APP
echo.
echo Stopping application...
call :STOP_APP_SILENT
echo Stopped.
pause
goto MENU

:STOP_APP_SILENT
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%BACKEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
exit /b
