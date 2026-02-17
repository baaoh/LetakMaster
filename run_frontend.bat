@echo off
cd /d "%~dp0frontend"
call npm run dev > ..\frontend_logs.txt 2>&1
