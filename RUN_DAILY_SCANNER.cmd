@echo off
setlocal
chcp 65001 >nul
set "PROJECT_ROOT=%~dp0"
set "PYTHONUTF8=1"
cd /d "%PROJECT_ROOT%"

if not exist "E:\python\python.exe" (
  echo Python was not found: E:\python\python.exe
  echo The scanner was not started.
  pause
  exit /b 9009
)

echo Running TDX Market Structure Scanner with local TDX daily data...
"E:\python\python.exe" "%PROJECT_ROOT%run_live_forward.py" --date latest
set "EXIT_CODE=%ERRORLEVEL%"

echo.
if "%EXIT_CODE%"=="0" (
  echo Completed successfully. Exit code: 0
) else (
  echo Run did not complete. Exit code: %EXIT_CODE%
)
echo Review the JSON result above and the reports directory.
pause
exit /b %EXIT_CODE%
