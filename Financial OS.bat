@echo off
title Cross-Border Financial OS
echo Booting Financial Engine...

rem Navigate to the directory where the batch file is located
cd /d "%~dp0"

rem Execute the main script using the virtual environment's Python
call .venv\Scripts\python.exe main.py

rem Close the command prompt window after the UI shuts down
exit