@echo off
setlocal EnableDelayedExpansion
:: LetakMaster v2.0 Collaborative Manager
set "AGENT_PORT=8001"
set "FRONTEND_PORT=5173"

:MENU
cls
echo ===================================================
echo      LetakMaster v2.0: Collaborative Manager
echo ===================================================
echo [1] Start Client (Hidden/Minimized + Browser)
echo [2] Stop All Local Servers
echo [3] Monitor Status
echo [4] Show Agent Logs (Tail)
echo [5] Start Client (Visible Terminals + Browser)
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
netstat -aon | find ":%AGENT_PORT%" | find "LISTENING" >nul
if !errorlevel!==0 (echo Agent    [Port %AGENT_PORT%]:  RUNNING) else (echo Agent    [Port %AGENT_PORT%]:  STOPPED)

netstat -aon | find ":%FRONTEND_PORT%" | find "LISTENING" >nul
if !errorlevel!==0 (echo Frontend [Port %FRONTEND_PORT%]:  RUNNING) else (echo Frontend [Port %FRONTEND_PORT%]:  STOPPED)
exit /b

:MONITOR_PAGE
cls
echo ===================================================
echo           Local Client Status
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
echo Stopping local agent and frontend...
call :KILL_SERVERS_SILENT
echo Stopped and windows closed.
pause
goto MENU

:START_SILENT
echo.
echo === Refreshing processes... ===
call :KILL_SERVERS_SILENT

:: Detect Python
set "PYTHON_EXE=python"
if exist ".\python_embed\python.exe" (
    set "PYTHON_EXE=.\python_embed\python.exe"
)

echo Starting Agent (Hidden)...
(
    echo @echo off
    echo title LetakMasterAgent_Proc
    echo cd /d "%%~dp0"
    echo set PYTHONPATH=%%CD%%
    echo "%PYTHON_EXE%" -m uvicorn client.main:app --host 0.0.0.0 --port %AGENT_PORT% --reload ^> agent_logs.txt 2^>^&1
) > run_agent.bat

wscript scripts\launch_silent.vbs run_agent.bat

echo Starting Frontend (Hidden)...
(
    echo @echo off
    echo title LetakMasterFrontend_Proc
    echo cd /d "%%~dp0frontend"
    echo call npm run dev ^> ..\frontend_logs.txt 2^>^&1
) > run_frontend.bat

wscript scripts\launch_silent.vbs run_frontend.bat

echo.
echo Waiting for initialization...
timeout /t 4 >nul
start http://localhost:%FRONTEND_PORT%
goto MENU

:START_VISIBLE
echo.
echo === Refreshing processes... ===
call :KILL_SERVERS_SILENT

:: Detect Python
set "PYTHON_EXE=python"
if exist ".\python_embed\python.exe" (
    set "PYTHON_EXE=.\python_embed\python.exe"
)

echo Starting Agent (Visible)...
start "LetakMasterAgent_Proc" cmd /k "set PYTHONPATH=%%CD%% && "%PYTHON_EXE%" -m uvicorn client.main:app --host 0.0.0.0 --port %AGENT_PORT% --reload"

echo Starting Frontend (Visible)...
cd frontend
start "LetakMasterFrontend_Proc" cmd /k "npm run dev"
cd ..

echo.
echo Waiting for launch...
timeout /t 4 >nul
start http://localhost:%FRONTEND_PORT%
goto MENU

:SHOW_LOGS
cls
echo ===================================================
echo           Agent Logs (Last 20 lines)
echo ===================================================
if exist agent_logs.txt (
    powershell -command "Get-Content agent_logs.txt -Tail 20"
) else (
    echo No agent_logs.txt found.
)
echo ===================================================
pause
goto MENU

:KILL_SERVERS_SILENT
:: 1. Kill by Port (Surgical)
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%AGENT_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| find ":%FRONTEND_PORT%" ^| find "LISTENING"') do taskkill /f /t /pid %%a >nul 2>&1

:: 2. Kill by Title (Using the exact Title from the start command)
taskkill /fi "windowtitle eq LetakMasterAgent_Proc" /f >nul 2>&1
taskkill /fi "windowtitle eq LetakMasterFrontend_Proc" /f >nul 2>&1
:: Also check for the window title with 'Admin:' prefix which Windows sometimes adds
taskkill /fi "windowtitle eq Administrator: LetakMasterAgent_Proc" /f >nul 2>&1
taskkill /fi "windowtitle eq Administrator: LetakMasterFrontend_Proc" /f >nul 2>&1
exit /b
