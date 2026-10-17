@echo off
setlocal EnableExtensions
title LeafyGreen - Uninstall

rem  --bundled: called by setup.py - no confirmation prompt or final pause,
rem  and whether to delete saved settings comes from LG_PURGE (y/n).
set "BUNDLED="
if /i "%~1"=="--bundled" set "BUNDLED=1"

set "APPNAME=LeafyGreen"
set "RULE=LeafyGreen Web Dashboard"
set "PF=%ProgramW6432%"
if not defined PF set "PF=%ProgramFiles%"
set "INSTALL=%PF%\%APPNAME%"
set "DATA=%ProgramData%\%APPNAME%"

echo.
echo  LeafyGreen uninstaller
echo  ------------------------
echo.

net session >nul 2>&1
if errorlevel 1 goto :needadmin

echo  This removes LeafyGreen from this computer. The child's
echo  apps and time limits will no longer be controlled.
echo.
if defined BUNDLED goto :confirmed
set "OK="
set /p "OK=Type YES to continue: "
if /i not "%OK%"=="YES" goto :cancel
:confirmed

echo.
echo  Stopping...
schtasks /End /TN "%APPNAME%" >nul 2>&1
schtasks /Delete /TN "%APPNAME%" /F >nul 2>&1
taskkill /F /IM %APPNAME%.exe >nul 2>&1
timeout /t 2 /nobreak >nul

echo  Unblocking websites and turning the network back on...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$h=Join-Path $env:SystemRoot 'System32\drivers\etc\hosts'; if(Test-Path $h){$t=[IO.File]::ReadAllText($h); $n=[regex]::Replace($t,'(?s)\r?\n?# >>> (?:LeafyGreen|Snort Secure) blocked websites.*?# <<< (?:LeafyGreen|Snort Secure) blocked websites <<<',''); if($n -ne $t){[IO.File]::WriteAllText($h,$n)}}" >nul 2>&1
ipconfig /flushdns >nul 2>&1
if exist "%DATA%\paused_adapters.txt" powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-Content -LiteralPath '%DATA%\paused_adapters.txt' | Where-Object { $_ } | ForEach-Object { Enable-NetAdapter -Name $_ -Confirm:$false -ErrorAction SilentlyContinue }" >nul 2>&1

echo  Removing files...
rem Old version (Snort Secure), if it is still there.
schtasks /End /TN "SnortSecure" >nul 2>&1
schtasks /Delete /TN "SnortSecure" /F >nul 2>&1
taskkill /F /IM SnortSecure.exe >nul 2>&1
netsh advfirewall firewall delete rule name="Snort Secure Web Dashboard" >nul 2>&1
if exist "%PF%\SnortSecure" rmdir /s /q "%PF%\SnortSecure"
netsh advfirewall firewall delete rule name="%RULE%" >nul 2>&1
if exist "%INSTALL%" rmdir /s /q "%INSTALL%"

echo.
if defined BUNDLED (
  set "DEL=%LG_PURGE%"
  goto :gotdel
)
set "DEL="
set /p "DEL=Also delete the saved settings and PIN? (y/N): "
:gotdel
if /i "%DEL%"=="y" if exist "%DATA%" rmdir /s /q "%DATA%"

echo.
echo  Done.
echo.
if not defined BUNDLED pause
exit /b 0

:needadmin
echo  This must be run as administrator.
echo  Right-click uninstall.bat and choose "Run as administrator".
echo.
pause
exit /b 1

:cancel
echo.
echo  Cancelled. Nothing was changed.
echo.
pause
exit /b 0
