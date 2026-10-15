@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Создаю виртуальное окружение...
  py -3 -m venv .venv || goto fail
)
.venv\Scripts\python.exe -m pip install -q -r requirements.txt || goto fail
start "" http://127.0.0.1:5000
.venv\Scripts\python.exe run.py
goto :eof
:fail
echo Не получилось подготовить окружение. Нужен Python 3 (команда py).
pause
