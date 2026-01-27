@echo off
echo ===================================================
echo           LetakMaster Dependency Installer
echo ===================================================

:: 0. Check for Bundled Python (Portable Mode)
set "PYTHON_EXE=python"
if exist ".\python_embed\python.exe" (
    echo [INFO] Bundled Python environment detected.
    set "PYTHON_EXE=.\python_embed\python.exe"
    goto SKIP_PYTHON_CHECK
)

:: 1. Check for System Python (Dev Mode)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed and no bundled runtime found.
    echo Please install Python 3.10+ from python.org or ensure 'python_embed/' is present.
    pause
    exit /b
)
echo [OK] System Python found.

:SKIP_PYTHON_CHECK
echo [OK] Using Python: %PYTHON_EXE%

:: 2. Check for Node.js / NPM
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] Node.js / NPM not found.
    echo Frontend development will be disabled. 
    echo You can still use the PORTABLE Integrated GUI via 'start_servers.bat'.
) else (
    echo [OK] NPM found.
)

echo.
echo ===================================================
echo [1/2] Installing/Verifying Python Dependencies...
echo ===================================================
"%PYTHON_EXE%" -m pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b
)

echo.
echo ===================================================
echo [2/2] Installing Frontend Dependencies (NPM)...
echo ===================================================
if exist "frontend\package.json" (
    cd frontend
    call npm install
    if %errorlevel% neq 0 (
        echo [WARNING] Failed to install NPM dependencies. 
        echo Dev mode might not work, but Portable mode is still available.
    )
    cd ..
) else (
    echo [INFO] frontend directory not found or incomplete. Skipping NPM install.
)

echo.
echo ===================================================
echo           Installation/Check Complete!
echo ===================================================
echo You can now run 'start_servers.bat'.
pause
