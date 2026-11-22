@echo off
cd /d "%~dp0"
if not exist data mkdir data
python agent.py --config config.example.json
if errorlevel 1 echo OM PC agent failed; review local console and Windows Task Scheduler history.
