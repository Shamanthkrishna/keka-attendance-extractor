@echo off
cd /d "D:\Shamanth_Krishna\Other\Keka Attendance Extractor"

REM Kill any previously running server instance on port 5000
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":5000 "') do (
    taskkill /F /PID %%a >nul 2>&1
)

REM Start the server hidden in the background
start "" /min pythonw server.py
echo Keka server started on port 5000.