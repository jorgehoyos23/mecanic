@echo off
chcp 65001 >nul
cd /d "%~dp0"
title Taller Mecanico - localhost:8080

rem 1) Si Docker funciona, usarlo
docker info >nul 2>&1
if %errorlevel%==0 goto CONDOCKER

rem 2) Intentar arrancar Docker Desktop (hasta ~90 s)
if exist "C:\Program Files\Docker\Docker\Docker Desktop.exe" (
  echo Arrancando Docker Desktop...
  start "" "C:\Program Files\Docker\Docker\Docker Desktop.exe"
  for /l %%i in (1,1,30) do (
    timeout /t 3 /nobreak >nul
    docker info >nul 2>&1 && goto CONDOCKER
  )
)

rem 3) Sin Docker: modo local (Python + SQLite)
echo.
echo Docker no esta disponible. Iniciando en modo local (sin Docker)...
start "" cmd /c "timeout /t 8 /nobreak >nul & start http://localhost:8080"
".venv\Scripts\python.exe" scripts\ejecutar_sin_docker.py
pause
exit /b

:CONDOCKER
echo Docker listo. Levantando contenedores...
docker compose up -d --build
start http://localhost:8080
echo.
echo Proyecto en http://localhost:8080  (para apagar: docker compose down)
pause
