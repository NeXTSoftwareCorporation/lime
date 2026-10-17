@echo off
setlocal EnableExtensions
title LeafyGreen - Install
cd /d "%~dp0"

rem ======================================================================
rem  Builds leafygreen.py into an exe, installs it to Program Files and
rem  runs it as a protected background task that a non-admin account can
rem  not stop, change or delete.
rem  Keep this file in the same folder as leafygreen.py and setup.py.
rem  This runs the install and then launches setup in one go.
rem  Re-run it any time to update (your settings are kept).
rem ======================================================================

rem  --bundled: called by setup.py - take the child account from LG_KID and
rem  do not prompt or pause (setup.py drives the flow and shows the result).
set "BUNDLED="
if /i "%~1"=="--bundled" set "BUNDLED=1"

set "APPNAME=LeafyGreen"
set "PORT=8765"
set "RULE=LeafyGreen Web Dashboard"
set "PF=%ProgramW6432%"
if not defined PF set "PF=%ProgramFiles%"
set "INSTALL=%PF%\%APPNAME%"
set "DATA=%ProgramData%\%APPNAME%"

echo.
echo  LeafyGreen installer
echo  ----------------------
echo.

net session >nul 2>&1
if errorlevel 1 goto :needadmin
if not exist "%~dp0leafygreen.py" goto :nosource
if not exist "%~dp0setup.py" goto :nosetup

set "PY="
py -3 --version >nul 2>&1 && set "PY=py -3"
if not defined PY python --version >nul 2>&1 && set "PY=python"
if not defined PY goto :nopython
%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)" >nul 2>&1
if errorlevel 1 goto :oldpython
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :notk

:askuser
if defined LG_KID (
  set "KID=%LG_KID%"
  goto :gotkid
)
set "KID="
set /p "KID=Windows account name of the child (as shown on the sign-in screen): "
if not defined KID goto :askuser
:gotkid
net user "%KID%" >nul 2>&1
if errorlevel 1 goto :baduser
net localgroup Administrators | findstr /i /x /c:"%KID%" >nul 2>&1
if not errorlevel 1 goto :kidisadmin

rem --- If the old version (Snort Secure) is installed, switch over to this one.
set "OLDAPP=SnortSecure"
schtasks /End /TN "%OLDAPP%" >nul 2>&1
schtasks /Delete /TN "%OLDAPP%" /F >nul 2>&1
taskkill /F /IM %OLDAPP%.exe >nul 2>&1
timeout /t 2 /nobreak >nul
netsh advfirewall firewall delete rule name="Snort Secure Web Dashboard" >nul 2>&1
if exist "%PF%\%OLDAPP%" rmdir /s /q "%PF%\%OLDAPP%"
if exist "%ProgramData%\%OLDAPP%" if not exist "%DATA%" move "%ProgramData%\%OLDAPP%" "%DATA%" >nul

echo.
echo  [1/6] Installing the build tool (needs internet the first time)...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 goto :pipfail

echo.
echo  [2/6] Building %APPNAME%.exe (this takes a minute)...
%PY% -m PyInstaller --noconfirm --clean --onedir --noconsole --name %APPNAME% --distpath "%~dp0build\dist" --workpath "%~dp0build\work" --specpath "%~dp0build" "%~dp0leafygreen.py"
if errorlevel 1 goto :buildfail
if not exist "%~dp0build\dist\%APPNAME%\%APPNAME%.exe" goto :buildfail

echo.
echo  [3/6] Stopping any running copy...
schtasks /End /TN "%APPNAME%" >nul 2>&1
taskkill /F /IM %APPNAME%.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo.
echo  [4/6] Copying to %INSTALL% ...
robocopy "%~dp0build\dist\%APPNAME%" "%INSTALL%" /MIR /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail

echo.
echo  [5/6] Locking the settings folder %DATA% ...
if not exist "%DATA%" mkdir "%DATA%"
if exist "%SystemDrive%\Users\%KID%\AppData\Roaming\%APPNAME%\settings.json" if not exist "%DATA%\settings.json" copy "%SystemDrive%\Users\%KID%\AppData\Roaming\%APPNAME%\settings.json" "%DATA%\settings.json" >nul
icacls "%DATA%" /inheritance:r /grant:r "*S-1-5-18:(OI)(CI)F" "*S-1-5-32-544:(OI)(CI)F" /T /C >nul
if errorlevel 1 goto :aclfail
rem Setup requests: ordinary users may only DROP files into inbox (they can not
rem read, list or change anything there). LeafyGreen answers in outbox (read only).
if not exist "%DATA%\inbox" mkdir "%DATA%\inbox"
if not exist "%DATA%\outbox" mkdir "%DATA%\outbox"
icacls "%DATA%\inbox" /grant "*S-1-5-32-545:(OI)(CI)(W)" >nul
if errorlevel 1 goto :aclfail
icacls "%DATA%\outbox" /grant "*S-1-5-32-545:(OI)(CI)(RX)" >nul
if errorlevel 1 goto :aclfail
icacls "%DATA%" /grant "*S-1-5-32-545:(X)" >nul
if errorlevel 1 goto :aclfail
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
netsh advfirewall firewall add rule name="%RULE%" dir=in action=allow protocol=TCP localport=%PORT% profile=private,domain program="%INSTALL%\%APPNAME%.exe" >nul

echo.
echo  [6/7] Setting it to start at boot and at every sign-in...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='Stop'; $a=New-ScheduledTaskAction -Execute '%INSTALL%\%APPNAME%.exe' -Argument '--launcher --user \"%KID%\"'; $t=@((New-ScheduledTaskTrigger -AtStartup),(New-ScheduledTaskTrigger -AtLogOn)); $s=New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries; $p=New-ScheduledTaskPrincipal -UserId 'SYSTEM' -LogonType ServiceAccount -RunLevel Highest; Register-ScheduledTask -TaskName '%APPNAME%' -Action $a -Trigger $t -Settings $s -Principal $p -Force | Out-Null"
if errorlevel 1 goto :taskfail
schtasks /Run /TN "%APPNAME%" >nul 2>&1

if defined BUNDLED goto :installed_ok

echo.
echo  ======================================================
echo   Install complete.
echo.
echo   NEXT: run setup.py to finish setup (it walks through all
echo   five steps). The easiest way is to just run setup.py from
echo   the start - it installs and sets up in one go.
echo.
echo   LeafyGreen starts by itself every time "%KID%"
echo   signs in and runs in the background; open it from the
echo   taskbar and use the PIN you chose in setup.
echo.
echo   Web Dashboard: http://THIS-PC-IP:%PORT%  (the address is
echo   shown in the LeafyGreen window). The network on this PC
echo   must be set to Private for other devices to connect.
echo   Pause Internet turns
echo   the network off, so resume it from the LeafyGreen window.
echo.
echo   To update, run this file again. To remove, run uninstall.bat.
echo  ======================================================
echo.
pause
:installed_ok
exit /b 0

:needadmin
echo  This must be run as administrator.
echo  Right-click install.bat and choose "Run as administrator".
echo.
pause
exit /b 1

:nosource
echo  Could not find leafygreen.py next to this file.
echo.
pause
exit /b 1

:nosetup
echo  Could not find setup.py next to this file. Keep install.bat,
echo  leafygreen.py and setup.py together in the same folder.
echo.
pause
exit /b 1

:nopython
echo  Python 3 was not found. Install it from python.org (tick "Add python.exe to PATH"
echo  and keep the tcl/tk option on), then run this again.
echo.
pause
exit /b 1

:oldpython
echo  Python 3.8 or newer is needed. Install a current version from python.org,
echo  then run this again.
echo.
pause
exit /b 1

:notk
echo  This Python has no tkinter (the window toolkit). Run the Python installer again,
echo  choose Modify, and tick "tcl/tk and IDLE". Then run this again.
echo.
pause
exit /b 1

:baduser
echo.
echo  There is no account called "%KID%" on this computer. Check the name and try again.
echo.
if defined LG_KID exit /b 1
goto :askuser

:kidisadmin
echo.
echo  "%KID%" is an administrator. The protection can not work for an administrator.
echo  Make the account a Standard user first (Settings, Accounts, Family and other users),
echo  then run this again.
echo.
pause
exit /b 1

:pipfail
echo  Could not install PyInstaller. Check the internet connection and try again.
echo.
pause
exit /b 1

:buildfail
echo  The build failed. Read the messages above for the reason.
echo.
pause
exit /b 1

:copyfail
echo  Could not copy the files to %INSTALL%.
echo.
pause
exit /b 1

:aclfail
echo  Could not lock the settings folder %DATA%.
echo.
pause
exit /b 1

:taskfail
echo  Could not create the startup task.
echo.
pause
exit /b 1
