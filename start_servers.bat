@echo off
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

:MENU
cls
echo ===================================================
echo           LetakMaster Server Manager
echo ===================================================
echo [1] Start / Restart Servers
echo [2] Kill Servers (Stop All)
echo [3] Monitor Status
echo [4] Exit
echo ===================================================
call :CHECK_STATUS
echo ===================================================
set /p choice=Enter selection: 

if "%choice%"=="1" goto START_SERVERS
if "%choice%"=="2" goto KILL_SERVERS
if "%choice%"=="3" goto MONITOR_PAGE
if "%choice%"=="4" exit
goto MENU

:CHECK_STATUS
netstat -aon | find ":%BACKEND_PORT%" | find "LISTENING" >nul
if %errorlevel%==0 (echo Backend  [Port %BACKEND_PORT%]:  RUNNING) else (echo Backend  [Port %BACKEND_PORT%]:  STOPPED)

netstat -aon | find ":%FRONTEND_PORT%" | find "LISTENING" >nul
if %errorlevel%==0 (echo Frontend [Port %FRONTEND_PORT%]:  RUNNING) else (echo Frontend [Port %FRONTEND_PORT%]:  STOPPED)
exit /b

:MONITOR_PAGE
cls
echo ===================================================
echo           Server Status
echo ===================================================
call :CHECK_STATUS
echo.
echo ===================================================
echo [R] Refresh Status
echo [M] Return to Menu
echo ===================================================
set /p mchoice=Enter selection: 
if /i "%mchoice%"=="R" goto MONITOR_PAGE
if /i "%mchoice%"=="M" goto MENU
goto MONITOR_PAGE

:KILL_SERVERS
echo.
echo Stopping existing servers...
call :KILL_SERVERS_SILENT
echo Servers stopped and windows closed.
pause
goto MENU

:START_SERVERS
echo.
echo === Killing old processes first... ===
call :KILL_SERVERS_SILENT

echo.
echo Starting Backend (Uvicorn)...
:: /c ensures window closes when process ends
start "LetakMaster Backend" cmd /c ".\python_embed\python.exe -m uvicorn app.main:app --host 0.0.0.0 --port %BACKEND_PORT% --reload"

echo Starting Frontend (Vite)...
cd frontend
:: /c ensures window closes when process ends
start "LetakMaster Frontend" cmd /c "npm run dev"
cd ..

echo.
echo ===================================================
echo Servers Launched!
echo Backend API: http://localhost:%BACKEND_PORT%/docs
echo Frontend GUI: http://localhost:%FRONTEND_PORT%
echo ===================================================
timeout /t 3 >nul
goto MENU

:KILL_SERVERS_SILENT
:: Using /f /t to kill process tree. Since windows use /c, they should auto-close when the child dies.
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%BACKEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%FRONTEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
exit /b
