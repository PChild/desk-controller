$ErrorActionPreference = "Stop"

$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = [Security.Principal.WindowsPrincipal]::new($identity)
$isAdministrator = $principal.IsInRole(
    [Security.Principal.WindowsBuiltInRole]::Administrator
)

if (-not $isAdministrator) {
    throw "Run this script from PowerShell opened with Run as administrator."
}

$agentPath = Join-Path $PSScriptRoot "movie_mode_agent.ps1"
$configPath = Join-Path $PSScriptRoot "movie_mode_agent_config.psd1"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Missing agent configuration: $configPath"
}

$runCommand = (
    'powershell.exe -NoProfile -ExecutionPolicy Bypass ' +
    '-WindowStyle Hidden -File "' +
    $agentPath +
    '"'
)

$runKey = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"

if (-not (Test-Path -LiteralPath $runKey)) {
    New-Item -Path $runKey -Force | Out-Null
}

Set-ItemProperty `
    -LiteralPath $runKey `
    -Name "DeskControllerMovieMode" `
    -Value $runCommand

$firewallRule = Get-NetFirewallRule `
    -DisplayName "Desk Controller Movie Mode" `
    -ErrorAction SilentlyContinue

if ($null -eq $firewallRule) {
    New-NetFirewallRule `
        -DisplayName "Desk Controller Movie Mode" `
        -Direction Inbound `
        -Action Allow `
        -Protocol UDP `
        -LocalPort 8765 `
        -Profile Private | Out-Null
}

$listener = Get-NetUDPEndpoint `
    -LocalPort 8765 `
    -ErrorAction SilentlyContinue

if ($null -eq $listener) {
    Start-Process `
        -FilePath "powershell.exe" `
        -ArgumentList @(
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-WindowStyle",
            "Hidden",
            "-File",
            $agentPath
        ) `
        -WindowStyle Hidden

    Start-Sleep -Seconds 2
}

$listener = Get-NetUDPEndpoint `
    -LocalPort 8765 `
    -ErrorAction SilentlyContinue

if ($null -eq $listener) {
    throw "Agent did not start listening on UDP port 8765."
}

Write-Host "Movie Mode agent installed and listening on UDP port 8765."
