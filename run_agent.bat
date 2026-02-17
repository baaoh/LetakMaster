@echo off
echo Starting LetakMaster Designer Agent...
set PYTHONPATH=%PYTHONPATH%;%CD%
python_embed\python.exe -m uvicorn client.main:app --host 0.0.0.0 --port 8001 --reload
pause
