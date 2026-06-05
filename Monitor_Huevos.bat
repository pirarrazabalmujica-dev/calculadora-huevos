@echo off
setlocal
title Monitor de Huevos
color 0A

:: ── Directorio de trabajo ───────────────────────────────────────────────────
set "WORK=%TEMP%\MHuevos"
if not exist "%WORK%" mkdir "%WORK%"

:: ── Copiar archivos desde la carpeta del BAT ────────────────────────────────
copy /y "%~dp0app.py"             "%WORK%\app.py"             >nul
copy /y "%~dp0importaciones.html" "%WORK%\importaciones.html" >nul
copy /y "%~dp0requirements.txt"   "%WORK%\requirements.txt"   >nul 2>nul

:: ── Verificar Python ─────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.9+ desde https://python.org
    pause
    exit /b 1
)

:: ── Instalar dependencias si faltan ─────────────────────────────────────────
echo Verificando dependencias...
python -c "import streamlit, requests, pandas, plotly, numpy, pdfplumber, xlrd, openpyxl, bs4, lxml" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias...
    pip install streamlit requests pandas plotly numpy pdfplumber xlrd openpyxl beautifulsoup4 lxml --quiet
)

:: ── Lanzar Streamlit ─────────────────────────────────────────────────────────
echo Iniciando Monitor de Huevos...
start "" http://localhost:8501
python -m streamlit run "%WORK%\app.py" --server.port 8501 --server.headless true

pause
