@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Build LeafyGreen Home Edition.exe

rem ======================================================================
rem  Builds setup.py into "LeafyGreen Home Edition.exe" - a double-click
rem  installer whose Windows UAC prompt reads "LeafyGreen Home Edition".
rem  Run this once on a Windows PC with Python (python.org) installed.
rem  Keep leafygreen.py, install.bat, uninstall.bat and setup_version.txt
rem  in this folder. Needs internet the first time (to get PyInstaller).
rem ======================================================================

if not exist "%~dp0setup.py" goto :missing
if not exist "%~dp0leafygreen.py" goto :missing
if not exist "%~dp0setup_version.txt" goto :missing

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto :nopython

echo.
echo  Installing the build tool (PyInstaller)...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :pipfail

echo.
echo  Building "LeafyGreen Home Edition.exe" (takes a minute)...
%PY% -m PyInstaller --noconfirm --clean --onefile --noconsole --uac-admin ^
  --name "LeafyGreen Home Edition" --version-file "%~dp0setup_version.txt" ^
  --distpath "%~dp0" --workpath "%~dp0build-setup\work" ^
  --specpath "%~dp0build-setup" "%~dp0setup.py"
if errorlevel 1 goto :buildfail
if not exist "%~dp0LeafyGreen Home Edition.exe" goto :buildfail

echo.
echo  ======================================================
echo   Done. "LeafyGreen Home Edition.exe" is in this folder.
echo.
echo   To install: keep it next to leafygreen.py, install.bat and
echo   uninstall.bat, then double-click "LeafyGreen Home Edition.exe".
echo   The UAC prompt will read "LeafyGreen Home Edition"
echo   (publisher will still show as Unknown - that needs code signing).
echo  ======================================================
echo.
pause
exit /b 0

:missing
echo  Keep build_setup.bat next to setup.py, leafygreen.py and
echo  setup_version.txt (and install.bat / uninstall.bat).
echo.
pause
exit /b 1

:nopython
echo  Python 3 was not found. Install it from python.org (tick
echo  "Add python.exe to PATH"), then run this again.
echo.
pause
exit /b 1

:pipfail
echo  Could not install PyInstaller. Check the internet connection.
echo.
pause
exit /b 1

:buildfail
echo  The build failed. Read the messages above for the reason.
echo.
pause
exit /b 1
