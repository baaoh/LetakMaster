@echo off
set "BACKEND_PORT=8000"
set "FRONTEND_PORT=5173"

:MENU
cls
echo ===================================================
echo           LetakMaster Server Manager
echo ===================================================
echo [1] Start Servers (Hidden / Silent)
echo [2] Stop All Servers
echo [3] Monitor Status
echo [4] Show Backend Logs (Tail)
echo [5] Start Servers (VISIBLE / DEBUG MODE)
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
if %errorlevel%==0 (echo Backend  [Port %BACKEND_PORT%]:  RUNNING (Background)) else (echo Backend  [Port %BACKEND_PORT%]:  STOPPED)

netstat -aon | find ":%FRONTEND_PORT%" | find "LISTENING" >nul
if %errorlevel%==0 (echo Frontend [Port %FRONTEND_PORT%]:  RUNNING (Background)) else (echo Frontend [Port %FRONTEND_PORT%]:  STOPPED)
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
if exist ".\python_embed\pythonw.exe" (
    echo [INFO] Using Bundled Python (Silent): .\python_embed\pythonw.exe
    set "PYTHON_EXE=.\python_embed\pythonw.exe"
) else (
    echo [INFO] Using System Python
)

echo Starting Backend (Hidden)...
:: Launch Python directly with uvicorn via pythonw (no window)
:: Redirect output to logs.txt
start "" "%PYTHON_EXE%" -m uvicorn app.main:app --host 127.0.0.1 --port %BACKEND_PORT% > logs.txt 2>&1

echo Starting Frontend (Vite)...
cd frontend
:: npm run dev usually requires a window. We can try start /min
start /min "LetakMaster Frontend" cmd /c "npm run dev > ..\frontend_logs.txt 2>&1"
cd ..

echo.
echo ===================================================
echo Servers Launched in Background!
echo.
echo   Integrated GUI: http://localhost:%BACKEND_PORT%
echo   API Docs: http://localhost:%BACKEND_PORT%/docs
echo.
echo use Option [4] to view logs if needed.
echo ===================================================
timeout /t 3 >nul
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
