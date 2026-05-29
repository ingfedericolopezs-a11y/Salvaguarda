@echo off
title ROESAN - Conciliador Salvaguardar
color 0A

echo.
echo  ============================================
echo   ROESAN - Conciliador Mensual Salvaguardar
echo  ============================================
echo.

:: Verificar que Python este instalado
python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python no esta instalado en este equipo.
    echo.
    echo  Descargalo en: https://www.python.org/downloads/
    echo  Asegurate de marcar "Add Python to PATH" al instalar.
    echo.
    pause
    exit /b 1
)

:: Crear entorno virtual si no existe
if not exist ".venv" (
    echo  Configurando entorno por primera vez, espera un momento...
    echo.
    python -m venv .venv
)

:: Activar entorno virtual
call .venv\Scripts\activate.bat

:: Instalar dependencias si faltan
python -c "import flask, pandas, openpyxl" >nul 2>&1
if errorlevel 1 (
    echo  Instalando dependencias necesarias...
    echo.
    pip install -r requirements.txt --quiet
    echo  Instalacion completada.
    echo.
)

:: Crear carpetas necesarias
if not exist "outputs" mkdir outputs
if not exist "uploads" mkdir uploads

:: Abrir navegador despues de 2 segundos
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:5000"

echo  Servidor iniciado. Abriendo navegador en http://127.0.0.1:5000
echo.
echo  Para detener el servidor cierra esta ventana o presiona Ctrl+C
echo.

:: Iniciar servidor Flask
python app.py

pause
