@echo off
rem Eleicoes Roblox 2026 - inicia o site no Windows
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python nao encontrado. Instale em https://www.python.org/downloads/
  pause
  exit /b 1
)
echo Instalando dependencias...
python -m pip install -r requirements.txt
echo.
echo Abrindo o site em http://127.0.0.1:5000 ...
start "" http://127.0.0.1:5000
python app.py
pause
