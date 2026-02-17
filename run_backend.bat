@echo off
cd /d "%~dp0"
".\python_embed\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload > logs.txt 2>&1
