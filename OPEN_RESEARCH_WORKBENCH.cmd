@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "$pointerPath = Join-Path (Get-Location) 'reports\workbench\CURRENT_WORKBENCH.json'; if (-not (Test-Path -LiteralPath $pointerPath)) { Write-Error 'No current workbench. Run RUN_DAILY_SCANNER.cmd first.'; exit 1 }; $pointer = ConvertFrom-Json (Get-Content -Raw -Encoding UTF8 -LiteralPath $pointerPath); if (-not $pointer.workbench_path -or -not (Test-Path -LiteralPath $pointer.workbench_path)) { Write-Error 'The current workbench file does not exist.'; exit 1 }; Start-Process -FilePath $pointer.workbench_path"
set "EXIT_CODE=%ERRORLEVEL%"
if not "%EXIT_CODE%"=="0" (
  echo.
  echo Failed to open the research workbench. Exit code: %EXIT_CODE%
  pause
)
exit /b %EXIT_CODE%
