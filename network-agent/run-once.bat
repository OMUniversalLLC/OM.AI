@echo off
cd /d "%~dp0"
if not exist "config.json" (
 echo Copy config.example.json to config.json and verify the approved NVR address first.
 pause
 exit /b 1
)
py -3 monitor.py --config config.json --out private\latest.json
if errorlevel 1 (echo OM WiFi check failed. Review the output.)
pause
