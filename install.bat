@echo off
echo ===================================================
echo           LetakMaster Dependency Installer
echo ===================================================

:: 1. Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.10+ from python.org.
    pause
    exit /b
)
echo [OK] Python found.

:: 2. Check for Node.js / NPM
call npm --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js / NPM is not installed or not in PATH.
    echo Please install Node.js from nodejs.org to run the Frontend.
    echo.
    echo You can still run the Backend-only mode, but the Web UI requires Node.
    pause
    exit /b
)
echo [OK] NPM found.

echo.
echo ===================================================
echo [1/2] Installing Python Dependencies...
echo ===================================================
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b
)

echo.
echo ===================================================
echo [2/2] Installing Frontend Dependencies (NPM)...
echo ===================================================
cd frontend
call npm install
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install NPM dependencies.
    cd ..
    pause
    exit /b
)
cd ..

echo.
echo ===================================================
echo           Installation Complete!
echo ===================================================
echo You can now run 'start_servers.bat'.
pause
