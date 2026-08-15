@echo off
setlocal
cd /d "%~dp0.."
title Instalar Centro de Monitoreo Compensar
echo ==========================================
echo   INSTALACION MONITOREO COMPENSAR
echo ==========================================
where py >nul 2>&1
if errorlevel 1 (
  echo ERROR: Python no esta disponible con el comando py.
  pause & exit /b 1
)
if not exist ".venv\Scripts\python.exe" py -3.12 -m venv .venv
call ".venv\Scripts\activate.bat"
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m playwright install chromium
echo.
echo Instalacion terminada.
echo Ahora ejecuta ABRIR_MONITOREO.bat
pause
