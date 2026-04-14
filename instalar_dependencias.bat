@echo off
echo ============================================
echo  Instalando dependencias del proyecto...
echo ============================================
echo.

cd /d C:\DIPLOMADO\crud

echo [1/3] Instalando fpdf2...
venv\Scripts\pip.exe install fpdf2
echo.

echo [2/3] Instalando todas las dependencias...
venv\Scripts\pip.exe install -r requirements.txt
echo.

echo [3/3] Verificando instalacion...
venv\Scripts\python.exe -c "from fpdf import FPDF; print('[OK] fpdf2 instalado correctamente')"
venv\Scripts\python.exe -c "import openpyxl; print('[OK] openpyxl instalado correctamente')"
venv\Scripts\python.exe -c "import flask; print('[OK] flask instalado correctamente')"
echo.

echo ============================================
echo  Listo! Ahora ejecuta: python app.py
echo ============================================
pause
