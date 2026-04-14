@echo off
title Contabilidad Arroceras - Setup PDF
color 0A

echo.
echo  ==========================================
echo   Contabilidad Arroceras - Generador PDF
echo  ==========================================
echo.

:: Verificar Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo  [ERROR] Python no esta instalado o no esta en el PATH.
    echo  Descargalo desde: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo  [1/3] Python detectado:
python --version
echo.

:: Instalar fpdf2
echo  [2/3] Instalando fpdf2...
pip install fpdf2 --quiet
if %errorlevel% neq 0 (
    echo  [ERROR] No se pudo instalar fpdf2. Verifica tu conexion a internet.
    pause
    exit /b 1
)
echo  fpdf2 instalado correctamente.
echo.

:: Generar PDF
echo  [3/3] Generando design-system.pdf en tmp\...
cd /d "%~dp0"
python generate_pdf.py
if %errorlevel% neq 0 (
    echo.
    echo  [ERROR] El script fallo. Revisa el error arriba.
    pause
    exit /b 1
)

echo.
echo  ==========================================
echo   PDF generado en: tmp\design-system.pdf
echo  ==========================================
echo.

:: Abrir la carpeta tmp automaticamente
explorer "%~dp0tmp"

pause
