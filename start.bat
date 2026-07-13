@echo off
title ZapPro - Iniciando...
cd /d "%~dp0"

echo ========================================
echo   ZapPro - Iniciando servicos
echo ========================================
echo.
echo Django:   http://localhost:8000
echo WhatsApp: http://localhost:3001
echo Admin:    admin / admin123
echo.

echo Encerrando processos antigos nas portas 8000 e 3001...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3001" ^| findstr "LISTENING"') do taskkill /F /PID %%a >nul 2>&1
timeout /t 2 /nobreak >nul

start "ZapPro - Django" cmd /k "cd /d "%~dp0" && venv\Scripts\activate && python manage.py runserver"
timeout /t 2 /nobreak >nul
start "ZapPro - WhatsApp" cmd /k "cd /d "%~dp0whatsapp-service" && npm start"

echo.
echo Servicos iniciados. Acesse http://localhost:8000
echo Reconecte o WhatsApp em WhatsApp ^> Conexao se necessario.
pause
