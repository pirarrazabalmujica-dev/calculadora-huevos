@echo off
setlocal
title Monitor de Huevos
color 0A

:: ── Directorio de trabajo ───────────────────────────────────────────────────
set "WORK=%TEMP%\MHuevos"
if not exist "%WORK%" mkdir "%WORK%"

:: ── Copiar archivos desde la carpeta del BAT ────────────────────────────────
copy /y "%~dp0app.py"                   "%WORK%\app.py"                   >nul
copy /y "%~dp0importaciones.html"       "%WORK%\importaciones.html"       >nul
copy /y "%~dp0requirements.txt"         "%WORK%\requirements.txt"         >nul 2>nul
copy /y "%~dp0produccion_historica.json" "%WORK%\produccion_historica.json" >nul 2>nul

:: ── Verificar Python ─────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python no encontrado. Instala Python 3.9+ desde https://python.org
    echo         Importante: marca "Add Python to PATH" durante la instalacion.
    pause
    exit /b 1
)

:: ── Asegurar que pip exista (algunas instalaciones no lo traen en el PATH) ───
python -m ensurepip --default-pip >nul 2>&1

:: ── Instalar dependencias base si faltan ────────────────────────────────────
echo Verificando dependencias...
python -c "import streamlit, requests, pandas, plotly, numpy, pdfplumber, xlrd, openpyxl, bs4, lxml" >nul 2>&1
if errorlevel 1 (
    echo Instalando dependencias base... ^(puede tardar unos minutos^)
    python -m pip install --quiet streamlit requests pandas plotly numpy pdfplumber xlrd openpyxl beautifulsoup4 lxml
    if errorlevel 1 (
        echo [ERROR] No se pudieron instalar las dependencias base.
        echo         Revisa tu conexion a internet e intenta de nuevo.
        pause
        exit /b 1
    )
)

:: ── Instalar dependencias de OCR (proyecciones 2026) si faltan ──────────────
::    Se intenta solo una vez; si falla, la app igual funciona sin proyeccion.
python -c "import easyocr, fitz, PIL" >nul 2>&1
if errorlevel 1 (
    if not exist "%WORK%\.ocr_tried" (
        echo Instalando OCR para proyecciones 2026... ^(descarga grande, puede tardar^)
        python -m pip install --quiet easyocr pymupdf pillow
        if errorlevel 1 (
            echo [AVISO] No se pudo instalar el OCR. La app funcionara, pero sin
            echo         las proyecciones de produccion 2026. El resto es normal.
        )
        echo intentado> "%WORK%\.ocr_tried"
    )
)

:: ── Lanzar Streamlit ─────────────────────────────────────────────────────────
echo Iniciando Monitor de Huevos...
start "" http://localhost:8501
python -m streamlit run "%WORK%\app.py" --server.port 8501 --server.headless true

pause
