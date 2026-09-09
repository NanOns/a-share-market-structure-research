@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
start "Unified Workbench Service" /min python run_workbench_service.py --host 127.0.0.1 --port 28765
timeout /t 2 /nobreak >nul
start "" http://127.0.0.1:28765/
