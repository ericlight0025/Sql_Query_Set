@echo off
setlocal EnableExtensions EnableDelayedExpansion

set "SCRIPT_DIR=%~dp0"
set "SETTINGS_FILE=%SCRIPT_DIR%settings.json"
set "PYTHON_EXE=C:\DevWorkspace\googletts_package_shorts_venv\Scripts\python.exe"

if exist "%SETTINGS_FILE%" (
    call :load_python_exe_from_settings
)

if not exist "%PYTHON_EXE%" (
    echo Python not found: %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%SCRIPT_DIR%gui.py"
set "ERR=%errorlevel%"
if not "%ERR%"=="0" (
    echo.
    echo GUI failed to start. Error code: %ERR%
    pause
)
exit /b %ERR%

:load_python_exe_from_settings
set "RAW="
for /f "usebackq tokens=1,* delims=:" %%A in (`findstr /R /C:"\"python_exe\"[ ]*:" "%SETTINGS_FILE%"`) do (
    set "RAW=%%B"
    goto :found_python_exe
)
goto :eof

:found_python_exe
set "RAW=!RAW:,=!"
set "RAW=!RAW:"=!"
for /f "tokens=* delims= " %%P in ("!RAW!") do set "RAW=%%P"
set "RAW=!RAW:/=\!"
if not "!RAW!"=="" set "PYTHON_EXE=!RAW!"
goto :eof
