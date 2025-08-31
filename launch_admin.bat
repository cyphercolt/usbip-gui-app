@echo off
:: USB/IP GUI Application Launcher with Admin Privileges
:: This script launches the USB/IP GUI application with administrator privileges on Windows

echo ========================================
echo USB/IP GUI Application Launcher
echo ========================================
echo.

:: Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with administrator privileges
    echo.
) else (
    echo ⚠️  Not running as administrator
    echo 🚀 Requesting administrator privileges...
    echo.
    
    :: Request administrator privileges
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d %CD% && call %~f0' -Verb runAs"
    exit /b
)

:: Change to the script directory
cd /d "%~dp0"

:: Check if virtual environment exists
if exist ".venv\Scripts\python.exe" (
    echo 🐍 Using virtual environment
    ".venv\Scripts\python.exe" src\main.py
) else (
    echo 🐍 Using system Python
    python src\main.py
)

echo.
echo 📋 Application closed. Press any key to exit...
pause >nul
