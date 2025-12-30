@echo off
TITLE Servidor GRID-Chat
COLOR 0B
echo =================================================
echo    INICIANDO GRID-CHAT - MODO ATOMICO
echo =================================================
echo.

echo [*] Activando entorno virtual...
call venv\Scripts\activate.bat

echo [*] Arrancando servidor Flask-SocketIO...
echo.
echo    [IMPORTANTE] Abre tu navegador en: http://127.0.0.1:5000
echo.
python app.py

pause