@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo تعذر تثبيت المكتبات. تأكد من اتصال الإنترنت ثم حاول مرة أخرى.
  pause
  exit /b 1
)
python app.py
pause
