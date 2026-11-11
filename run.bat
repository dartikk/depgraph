@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (set "PY=python") else (set "PY=py")
if /i "%1"=="test" goto tests
%PY% src\main.py %*
goto :eof
:tests
%PY% -m unittest discover -s tests -t . -v
