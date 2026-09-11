@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"
set "PYTHON_EXE=E:\python\python.exe"
if not exist "%PYTHON_EXE%" set "PYTHON_EXE=python"
start "Unified Workbench Service" /min "%PYTHON_EXE%" "%PROJECT_ROOT%run_workbench_service.py" --host 127.0.0.1 --port 28765

powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$deadline=(Get-Date).AddSeconds(65); do { try { $response=Invoke-WebRequest -UseBasicParsing -Uri 'http://127.0.0.1:28765/v2' -TimeoutSec 2; if ($response.StatusCode -eq 200) { Start-Process 'http://127.0.0.1:28765/v2'; exit 0 } } catch {}; Start-Sleep -Milliseconds 500 } while ((Get-Date) -lt $deadline); Write-Error 'Unified Workbench Service did not become ready within 65 seconds.'; exit 1"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Failed to start the unified workbench service. Exit code: %EXIT_CODE%
  pause
)
exit /b %EXIT_CODE%
