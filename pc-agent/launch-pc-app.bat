@echo off
cd /d "%~dp0"
py desktop_app.py
if errorlevel 1 (
 echo Could not start OM AI PC Companion. Verify Python and Tkinter installation.
 pause
)
