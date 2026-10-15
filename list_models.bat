@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (.venv\Scripts\python.exe list_models.py) else (py -3 list_models.py)
pause
