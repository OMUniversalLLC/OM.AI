@echo off
title OM AI Vehicle Traffic
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Start-OMAI.ps1" %*
if errorlevel 1 pause
