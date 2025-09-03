# USB/IP GUI Application Launcher with Admin Privileges (PowerShell)
# This script launches the USB/IP GUI application with administrator privileges on Windows

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "USB/IP GUI Application Launcher" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check if running as administrator
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

if ($isAdmin) {
    Write-Host "✅ Running with administrator privileges" -ForegroundColor Green
    Write-Host ""
} else {
    Write-Host "⚠️  Not running as administrator" -ForegroundColor Yellow
    Write-Host "🚀 Requesting administrator privileges..." -ForegroundColor Blue
    Write-Host ""
    
    # Request administrator privileges
    try {
        $scriptPath = $MyInvocation.MyCommand.Path
        Start-Process PowerShell -ArgumentList "-File `"$scriptPath`"" -Verb RunAs
        exit
    } catch {
        Write-Host "❌ Failed to elevate privileges: $($_.Exception.Message)" -ForegroundColor Red
        Write-Host "Please right-click the script and select 'Run as administrator'" -ForegroundColor Yellow
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Change to the project root directory (parent of scripts directory)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir
Set-Location $projectRoot

Write-Host "📁 Project root: $projectRoot" -ForegroundColor Blue

# Check if virtual environment exists
if (Test-Path "venv\Scripts\python.exe") {
    Write-Host "🐍 Using virtual environment" -ForegroundColor Green
    $pythonPath = ".\venv\Scripts\python.exe"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
    Write-Host "🐍 Using system Python" -ForegroundColor Green
    $pythonPath = "python"
} else {
    Write-Host "❌ Python not found. Please install Python or set up the virtual environment." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

try {
    Write-Host "🚀 Starting USB/IP GUI Application..." -ForegroundColor Blue
    Write-Host ""
    
    # Launch the application
    & $pythonPath "src\main.py"
    
} catch {
    Write-Host "❌ Error launching application: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 Application closed. Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
