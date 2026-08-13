@echo off
title CY_BORG Map Server
echo ============================================
echo   Avvio server locale per la mappa di Cy...
echo ============================================
echo.
echo Una volta avviato, apri nel browser:
echo   http://localhost:8000/cy-borg-map.html
echo.
echo Per chiudere il server, chiudi questa finestra
echo oppure premi CTRL+C.
echo.
cd /d "%~dp0"
python -m http.server 8000
pause