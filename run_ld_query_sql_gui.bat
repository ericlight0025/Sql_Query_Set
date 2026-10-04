@echo off
setlocal EnableExtensions

set "SCRIPT_DIR=%~dp0"
set "SETTINGS_FILE=%SCRIPT_DIR%settings.json"
set "PYTHON_EXE="
set "PYTHON_ARGS="

if exist "%SETTINGS_FILE%" (
    for /f "usebackq delims=" %%P in (`powershell -NoProfile -Command "$s = ConvertFrom-Json -InputObject ([IO.File]::ReadAllText($env:SETTINGS_FILE)); if ($s.python_exe) { $p = $s.python_exe; if (-not [IO.Path]::IsPathRooted($p)) { $r = $s.root_dir; if (-not $r) { $r = '.' }; if (-not [IO.Path]::IsPathRooted($r)) { $r = Join-Path $env:SCRIPT_DIR $r }; $p = Join-Path $r $p }; [Console]::WriteLine($p) }"`) do set "PYTHON_EXE=%%P"
)
if defined PYTHON_EXE goto configured

where py >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=py"
    set "PYTHON_ARGS=-3"
    goto run
)
where python >nul 2>&1
if not errorlevel 1 (
    set "PYTHON_EXE=python"
    goto run
)
echo Python 3.11 or newer is required. Install Python or set python_exe in settings.json.
pause
exit /b 1

:configured
if exist "%PYTHON_EXE%" goto run
echo Python not found: "%PYTHON_EXE%"
pause
exit /b 1

:run
"%PYTHON_EXE%" %PYTHON_ARGS% "%SCRIPT_DIR%gui.py"
set "ERR=%errorlevel%"
if "%ERR%"=="0" exit /b 0
echo GUI failed to start. Error code: %ERR%
pause
exit /b %ERR%
