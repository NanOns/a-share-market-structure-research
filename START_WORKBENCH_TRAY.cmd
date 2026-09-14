@echo off
setlocal
cd /d "%~dp0"
start "DaA Workbench Tray" /min powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "%~dp0scripts\workbench_tray.ps1" -OpenWorkbench
exit /b 0
