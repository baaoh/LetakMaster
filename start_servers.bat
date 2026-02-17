@echo off
setlocal EnableDelayedExpansion
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

:MENU
cls
echo ===================================================
echo           LetakMaster Server Manager
echo ===================================================
echo [1] Start Servers (Hidden/Minimized + Browser)
echo [2] Stop All Servers
echo [3] Monitor Status
echo [4] Show Backend Logs (Tail)
echo [5] Start Servers (Visible Terminals + Browser)
echo [6] Exit
echo ===================================================
call :CHECK_STATUS
echo ===================================================
set /p choice=Enter selection: 

if "%choice%"=="1" goto START_SILENT
if "%choice%"=="2" goto KILL_SERVERS
if "%choice%"=="3" goto MONITOR_PAGE
if "%choice%"=="4" goto SHOW_LOGS
if "%choice%"=="5" goto START_VISIBLE
if "%choice%"=="6" exit
goto MENU

:CHECK_STATUS
netstat -aon | find ":%BACKEND_PORT%" | find "LISTENING" >nul
if !errorlevel!==0 (echo Backend  [Port %BACKEND_PORT%]:  RUNNING) else (echo Backend  [Port %BACKEND_PORT%]:  STOPPED)

netstat -aon | find ":%FRONTEND_PORT%" | find "LISTENING" >nul
if !errorlevel!==0 (echo Frontend [Port %FRONTEND_PORT%]:  RUNNING) else (echo Frontend [Port %FRONTEND_PORT%]:  STOPPED)
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
echo Servers stopped.
pause
goto MENU

:START_SILENT
echo.
echo === Killing old processes first... ===
call :KILL_SERVERS_SILENT

:: Detect Python
set "PYTHON_EXE=python"
if exist ".\python_embed\python.exe" (
    echo [INFO] Using Bundled Python: .\python_embed\python.exe
    set "PYTHON_EXE=.\python_embed\python.exe"
)

echo Starting Backend (Hidden)...
:: Create a temp runner for backend
(
    echo @echo off
    echo cd /d "%%~dp0"
    echo "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% --reload ^> logs.txt 2^>^&1
) > run_backend.bat

:: Launch it silently
wscript scripts\launch_silent.vbs run_backend.bat

echo Starting Frontend (Hidden)...
:: Create a temp runner for frontend
(
    echo @echo off
    echo cd /d "%%~dp0frontend"
    echo call npm run dev ^> ..\frontend_logs.txt 2^>^&1
) > run_frontend.bat

:: Launch it silently
wscript scripts\launch_silent.vbs run_frontend.bat

echo.
echo Waiting for servers to initialize...
timeout /t 4 >nul
echo Opening Browser...
start http://localhost:%BACKEND_PORT%

goto MENU

:START_VISIBLE
echo.
echo === Killing old processes first... ===
call :KILL_SERVERS_SILENT

:: Detect Python
set "PYTHON_EXE=python"
if exist ".\python_embed\python.exe" (
    echo [INFO] Using Bundled Python: .\python_embed\python.exe
    set "PYTHON_EXE=.\python_embed\python.exe"
)

echo Starting Backend (Visible)...
start "LetakMaster Backend" cmd /k ""%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% --reload"

echo Starting Frontend (Visible)...
cd frontend
start "LetakMaster Frontend" cmd /k "npm run dev"
cd ..

echo.
echo Waiting for servers...
timeout /t 4 >nul
echo Opening Browser...
:: In Visible/Dev mode, we prefer the Frontend Port (Vite) if available, 
:: but fallback to Backend if Node isn't running well.
start http://localhost:%FRONTEND_PORT%

goto MENU

:SHOW_LOGS
cls
echo ===================================================
echo           Backend Logs (Last 20 lines)
echo ===================================================
if exist logs.txt (
    powershell -command "Get-Content logs.txt -Tail 20"
) else (
    echo No logs.txt found.
)
echo ===================================================
pause
goto MENU

:KILL_SERVERS_SILENT
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%BACKEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%FRONTEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
exit /b
