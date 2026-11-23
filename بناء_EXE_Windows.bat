@echo off
chcp 65001 >nul
cd /d "%~dp0"
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo تعذر تثبيت المكتبات.
  pause
  exit /b 1
)
python -m PyInstaller --noconfirm --clean --windowed --onefile --name "نظام أرشفة المستندات" --add-data "index.html;." app.py
if errorlevel 1 (
  echo فشل بناء EXE. راجع رسائل الخطأ أعلاه.
  pause
  exit /b 1
)
echo.
echo اكتمل البناء. ستجد البرنامج داخل مجلد dist.
pause
