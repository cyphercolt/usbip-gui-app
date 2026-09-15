# Install usbip-node as a boot service on Windows. Run in an ELEVATED PowerShell:
#     Set-ExecutionPolicy -Scope Process Bypass -Force
#     .\packaging\install-windows.ps1
#
# STATUS: ported from the old app's known-good Windows USB/IP commands but NOT yet verified on
# real Windows hardware. Test with care.
#
# Windows needs two upstream tools:
#   * usbipd-win  (server: share this PC's devices)  -> winget install usbipd
#   * usbip-win2  (client: attach a remote device)   -> https://github.com/vadimgrn/usbip-win2/releases
#
# This script sets up the node itself: a Python venv, a firewall rule, and a scheduled task that
# runs the node as SYSTEM at boot (so usbipd/usbip need no UAC prompt).

$ErrorActionPreference = "Stop"
$Port = 4820
$RepoDir = (Resolve-Path "$PSScriptRoot\..").Path
$Venv = Join-Path $RepoDir "node\.venv"

function Assert-Admin {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = New-Object Security.Principal.WindowsPrincipal($id)
    if (-not $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Please run this in an elevated (Administrator) PowerShell."
    }
}
Assert-Admin

Write-Host "==> Checking prerequisites"
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    throw "Python not found. Install Python 3 (python.org) and re-run."
}
if (-not (Get-Command usbipd -ErrorAction SilentlyContinue)) {
    Write-Warning "usbipd-win not found. Install it to SHARE devices from this PC:  winget install usbipd"
}
# usbip-win2 installs to Program Files\USBip but does not add itself to PATH, and the node runs
# `usbip` by name. Put it on the system PATH so the SYSTEM boot task can find it.
$UsbipDir = Join-Path $env:ProgramFiles "USBip"
if ((Test-Path "$UsbipDir\usbip.exe") -and -not (Get-Command usbip -ErrorAction SilentlyContinue)) {
    $envKey = [Microsoft.Win32.Registry]::LocalMachine.OpenSubKey("SYSTEM\CurrentControlSet\Control\Session Manager\Environment", $true)
    $rawPath = $envKey.GetValue("Path", "", "DoNotExpandEnvironmentNames")
    if (($rawPath -split ";") -notcontains $UsbipDir) {
        $envKey.SetValue("Path", ($rawPath.TrimEnd(";") + ";" + $UsbipDir), "ExpandString")
        Write-Host "    Added $UsbipDir to the system PATH"
    }
    $envKey.Close()
    $env:Path += ";$UsbipDir"
}
if (-not (Get-Command usbip -ErrorAction SilentlyContinue)) {
    Write-Warning "usbip-win2 client not found. Install it to ATTACH devices to this PC:  winget install vadimgrn.usbip-win2"
}

# Keep this file ASCII-only: Windows PowerShell 5.1 reads BOM-less scripts as ANSI, and a UTF-8
# em dash decodes to a curly quote that breaks string parsing.
if (-not (Test-Path "$RepoDir\web\dist\index.html")) {
    throw "web\dist missing. It ships prebuilt on the branch - run 'git pull', or build with 'cd web; npm install; npm run build'."
}

$UpdateBranch = $env:USBIP_NODE_UPDATE_BRANCH
if (-not $UpdateBranch) { $UpdateBranch = "main" }

# A running node holds the venv's pythonw.exe open (so `venv` can't rewrite it) and would keep
# serving the old code, since Start-ScheduledTask below is a no-op while the task is running.
# Kill just that process rather than Stop-ScheduledTask: the in-app updater runs this script as a
# child of the task, and stopping the task could take the updater down with it.
$running = Get-Process pythonw -ErrorAction SilentlyContinue | Where-Object { $_.Path -eq "$Venv\Scripts\pythonw.exe" }
if ($running) {
    Write-Host "==> Stopping the running node"
    $running | Stop-Process -Force
    $running | Wait-Process -Timeout 15 -ErrorAction SilentlyContinue
}

Write-Host "==> Creating Python venv + installing usbip-node"
python -m venv $Venv
& "$Venv\Scripts\python.exe" -m pip install --quiet --upgrade pip
# Editable install so the node finds the committed web\dist via its own path.
& "$Venv\Scripts\python.exe" -m pip install --quiet -e "$RepoDir\node"

Write-Host "==> Copying updater"
Copy-Item "$RepoDir\packaging\update.ps1" "$RepoDir\update.ps1" -Force | Out-Null

# The updater runs git as SYSTEM, which refuses a checkout owned by another user ("detected
# dubious ownership"). Trust this one repo system-wide so in-app updates work.
if (Get-Command git -ErrorAction SilentlyContinue) {
    $SafeDir = $RepoDir -replace '\\', '/'
    if (-not (git config --system --get-all safe.directory | Where-Object { $_ -eq $SafeDir })) {
        Write-Host "==> Trusting $SafeDir for git (updater runs as SYSTEM)"
        git config --system --add safe.directory $SafeDir
    }
}

Write-Host "==> Opening firewall port $Port"
if (-not (Get-NetFirewallRule -DisplayName "usbip-node" -ErrorAction SilentlyContinue)) {
    New-NetFirewallRule -DisplayName "usbip-node" -Direction Inbound -Action Allow `
        -Protocol TCP -LocalPort $Port | Out-Null
}

Write-Host "==> Registering boot task (runs as SYSTEM)"
$pyw = "$Venv\Scripts\pythonw.exe"
$action = New-ScheduledTaskAction -Execute $pyw -Argument "-m usbip_node" -WorkingDirectory $RepoDir
$trigger = New-ScheduledTaskTrigger -AtStartup
$principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
Register-ScheduledTask -TaskName "usbip-node" -Action $action -Trigger $trigger `
    -Principal $principal -Settings $settings -Force | Out-Null
Start-ScheduledTask -TaskName "usbip-node"

$ip = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.PrefixOrigin -ne 'WellKnown' -and $_.IPAddress -notlike '169.*' } | Select-Object -First 1).IPAddress
Write-Host ""
Write-Host "==> Done. usbip-node is running (as SYSTEM, starts on boot)."
Write-Host "    Open from any phone/PC on the LAN:  http://$ip`:$Port"
Write-Host "    Manage: Task Scheduler -> usbip-node   (Start/Stop/Disable)"
Write-Host "    Update branch: $UpdateBranch"
Write-Host "    Update later: use the Updates page, or run .\update.ps1"
