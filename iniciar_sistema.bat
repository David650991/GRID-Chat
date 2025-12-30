@echo off
TITLE Servidor Chat Atomico
COLOR 0A
echo =================================================
echo    INICIANDO SISTEMA DE CHAT - MODO ATOMICO
echo =================================================
echo.

:: 1. Activar entorno virtual
echo [*] Activando entorno virtual...
call venv\Scripts\activate.bat

:: 2. Ejecutar la aplicacion correctamente
echo [*] Arrancando servidor Flask-SocketIO...
echo.
echo    [IMPORTANTE] No cierres esta ventana.
echo    Abre tu navegador en: http://127.0.0.1:5000
echo.

python app.py

pause