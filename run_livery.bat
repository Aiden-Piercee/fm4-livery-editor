@echo off
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Use "FM4 Livery Tool.exe" from the Windows download instead - it needs nothing installed.
  pause
  exit /b 1
)
python "%~dp0run_livery.py" %*
