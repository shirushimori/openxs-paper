@echo off
setlocal EnableDelayedExpansion

set "APP_NAME=OpenXS Paper"
set "REQUIRED_PYTHON=3.12.0"
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
set "PYTHON_CMD="

echo.
echo  =============================================
echo   %APP_NAME% - Installer ^& Launcher
echo  =============================================
echo.

:: ─────────────────────────────────────────────
:: 1. Find Python 3.12
:: ─────────────────────────────────────────────
echo [*] Checking for Python 3.12...

for %%C in (python3.12 python py) do (
    if "!PYTHON_CMD!"=="" (
        where %%C >nul 2>&1
        if !errorlevel! == 0 (
            for /f "tokens=2 delims= " %%V in ('%%C --version 2^>^&1') do (
                echo %%V | findstr /b "3.12" >nul
                if !errorlevel! == 0 (
                    set "PYTHON_CMD=%%C"
                )
            )
        )
    )
)

if "!PYTHON_CMD!"=="" (
    echo [!] Python 3.12 not found. Attempting to install...
    goto :install_python
)

echo [+] Found Python 3.12: !PYTHON_CMD!
goto :setup_venv

:: ─────────────────────────────────────────────
:: 2. Install Python 3.12
:: ─────────────────────────────────────────────
:install_python
where winget >nul 2>&1
if %errorlevel% == 0 (
    echo [*] Installing Python 3.12 via winget...
    winget install --id Python.Python.3.12 --version 3.12.0 --accept-source-agreements --accept-package-agreements
    if !errorlevel! == 0 (
        echo [+] Python installed via winget.
        call refreshenv >nul 2>&1
        set "PYTHON_CMD=python"
        goto :setup_venv
    )
)

where choco >nul 2>&1
if %errorlevel% == 0 (
    echo [*] Installing Python 3.12 via Chocolatey...
    choco install python312 -y
    if !errorlevel! == 0 (
        echo [+] Python installed via Chocolatey.
        call refreshenv >nul 2>&1
        set "PYTHON_CMD=python"
        goto :setup_venv
    )
)

echo.
echo [ERROR] Could not install Python automatically.
echo         Please install Python 3.12 from https://www.python.org/downloads/
echo         Then re-run this script.
pause
exit /b 1

:: ─────────────────────────────────────────────
:: 3. Create / reuse venv
:: ─────────────────────────────────────────────
:setup_venv
if exist "%VENV_DIR%\Scripts\python.exe" (
    echo [+] Virtual environment already exists.
) else (
    echo [*] Creating virtual environment...
    !PYTHON_CMD! -m venv "%VENV_DIR%"
    if !errorlevel! neq 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [+] Virtual environment created.
)

set "VENV_PYTHON=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: ─────────────────────────────────────────────
:: 4. Install dependencies
:: ─────────────────────────────────────────────
echo [*] Installing dependencies...
"%VENV_PIP%" install --upgrade pip --quiet
"%VENV_PIP%" install -r "%SCRIPT_DIR%requirements.txt" --quiet
if !errorlevel! neq 0 (
    echo [ERROR] pip install failed.
    pause
    exit /b 1
)
echo [+] Dependencies ready.

:: ─────────────────────────────────────────────
:: 5. Create Desktop shortcut
:: ─────────────────────────────────────────────
echo [*] Creating Desktop shortcut...
set "SHORTCUT_PATH=%USERPROFILE%\Desktop\%APP_NAME%.lnk"
set "ICON_PATH=%SCRIPT_DIR%assets\icons\logo.ico"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%SHORTCUT_PATH%'); ^
   $s.TargetPath = '%SCRIPT_DIR%start.bat'; ^
   $s.WorkingDirectory = '%SCRIPT_DIR%'; ^
   if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; ^
   $s.Description = 'OpenXS Paper - Live Wallpaper Engine'; ^
   $s.Save()"
echo [+] Desktop shortcut created.

:: ─────────────────────────────────────────────
:: 6. Create Start Menu shortcut
:: ─────────────────────────────────────────────
echo [*] Creating Start Menu shortcut...
set "STARTMENU_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\%APP_NAME%"
if not exist "%STARTMENU_DIR%" mkdir "%STARTMENU_DIR%"
set "STARTMENU_SHORTCUT=%STARTMENU_DIR%\%APP_NAME%.lnk"

powershell -NoProfile -Command ^
  "$ws = New-Object -ComObject WScript.Shell; ^
   $s = $ws.CreateShortcut('%STARTMENU_SHORTCUT%'); ^
   $s.TargetPath = '%SCRIPT_DIR%start.bat'; ^
   $s.WorkingDirectory = '%SCRIPT_DIR%'; ^
   if (Test-Path '%ICON_PATH%') { $s.IconLocation = '%ICON_PATH%' }; ^
   $s.Description = 'OpenXS Paper - Live Wallpaper Engine'; ^
   $s.Save()"
echo [+] Start Menu shortcut created.

:: ─────────────────────────────────────────────
:: 7. Launch app
:: ─────────────────────────────────────────────
echo.
echo [*] Starting %APP_NAME%...
echo.
cd /d "%SCRIPT_DIR%"
"%VENV_PYTHON%" main.py
endlocal
