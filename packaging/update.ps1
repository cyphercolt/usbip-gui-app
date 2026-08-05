# Out-of-process updater for usbip-node on Windows.
# Run by the node service when the user clicks Update. Do not run directly unless testing.
$ErrorActionPreference = "Stop"

$RepoDir = (Resolve-Path "$PSScriptRoot\..").Path
$Branch = $env:USBIP_NODE_UPDATE_BRANCH
if (-not $Branch) { $Branch = "main" }

if (-not (Test-Path "$RepoDir\.git")) {
    Write-Error "No git checkout at $RepoDir"
}

Set-Location $RepoDir

Write-Host "==> Tagging current commit as rollback point"
$Tag = "pre-update-$(Get-Date -Format yyyyMMddHHmmss)"
git tag $Tag 2>$null

Write-Host "==> Fetching origin"
git fetch origin

Write-Host "==> Updating to origin/$Branch"
git reset --hard "origin/$Branch"

Write-Host "==> Re-installing service"
$env:USBIP_NODE_UPDATE_BRANCH = $Branch
.\packaging\install-windows.ps1
