@echo off
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0Install-wsc-local.ps1" %*
pause
