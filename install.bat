@echo off
echo ===================================================
echo           LetakMaster Installer
echo ===================================================

:: Check for Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not found in your PATH.
    echo Please install Python 3.10 or newer and make sure to check "Add Python to PATH" during installation.
    echo Download: https://www.python.org/downloads/
    pause
    exit /b
)

echo [1/3] Creating virtual environment...
python -m venv venv

echo [2/3] Installing dependencies...
call venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt

echo [3/3] Creating launch script...
(
echo @echo off
echo call venv\Scripts\activate
echo start "LetakMaster Backend" cmd /c "python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo timeout /t 2 ^>nul
echo start http://localhost:8000
echo echo Application is running...
echo pause
) > start_app.bat

echo ===================================================
echo           Installation Complete!
echo ===================================================
echo You can now run 'start_app.bat' to launch the application.
pause
