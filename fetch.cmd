@echo off
setlocal
set "PYRUN="
py -3 --version >nul 2>nul && set "PYRUN=py -3"
if not defined PYRUN python --version >nul 2>nul && set "PYRUN=python"
if not defined PYRUN (
  echo Python 3 is not installed on this computer.
  echo Get it free from https://www.python.org/downloads/ and tick "Add python.exe to PATH" in the installer,
  echo then run this file again.
  pause
  exit /b 1
)
set "PYTHONPATH=%~dp0src"
%PYRUN% -m lightsout.fetch %*
if errorlevel 1 (
  echo.
  echo Something went wrong - see the message above.
  pause
)
