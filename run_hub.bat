@echo off
echo Starting LetakMaster Hub (Local Mode)...
set PYTHONPATH=%PYTHONPATH%;%CD%
python_embed\python.exe -m uvicorn server.main:app --host 0.0.0.0 --port 8000 --reload
pause
