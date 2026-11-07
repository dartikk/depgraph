@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (set "PY=py") else (set "PY=python")
if /i "%1"=="test" goto tests
%PY% src\main.py %*
goto :eof
:tests
%PY% -m unittest discover -s tests -t . -v
