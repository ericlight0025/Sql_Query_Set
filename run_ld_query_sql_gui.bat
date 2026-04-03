@echo off
setlocal

set "PYTHON_EXE=C:\DevWorkspace\googletts_package_shorts_venv\Scripts\python.exe"
set "SCRIPT_DIR=%~dp0"

if not exist "%PYTHON_EXE%" (
    echo Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_DIR%gui.py"
exit /b %errorlevel%
