@echo off
REM start_chrome.bat
REM Launches Google Chrome with the remote debugging port enabled (9222).
REM This allows auto_extract.py to read the token from your open Keka tab
REM without opening a new window or asking you to log in.
REM
REM Place this in Windows Startup (done automatically by setup_scheduler.py)
REM so Chrome always starts with debugging enabled after every login.

REM Check if Chrome is already running with the debug port open
curl -s -o nul -w "%%{http_code}" http://localhost:9222/json 2>nul | findstr "200" >nul
if %errorlevel% == 0 (
    echo Chrome is already running with remote debugging on port 9222.
    exit /b 0
)

REM Chrome is not running with the debug port — launch it now.
REM NOTE: If Chrome is currently open WITHOUT the debug port you must close it first.
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
echo Chrome launched with --remote-debugging-port=9222
