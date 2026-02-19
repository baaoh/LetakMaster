@echo off
title LetakMasterAgent_Proc
cd /d "%~dp0"
set PYTHONPATH=%CD%
".\python_embed\python.exe" -m uvicorn client.main:app --host 0.0.0.0 --port 8001 --reload > agent_logs.txt 2>&1
