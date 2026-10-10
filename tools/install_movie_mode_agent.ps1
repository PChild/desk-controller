$ErrorActionPreference = "Stop"

$agentPath = Join-Path $PSScriptRoot "movie_mode_agent.ps1"
$configPath = Join-Path $PSScriptRoot "movie_mode_agent_config.psd1"

if (-not (Test-Path -LiteralPath $configPath)) {
    throw "Missing agent configuration: $configPath"
}

# Start the helper invisibly at each login in this user's interactive desktop.
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

$listener = Get-NetUDPEndpoint `
    -LocalPort 8765 `
    -ErrorAction SilentlyContinue

if ($null -ne $listener) {
    $listenerProcess = Get-Process `
        -Id $listener.OwningProcess `
        -ErrorAction SilentlyContinue

    if ($listenerProcess.Name -notin @("powershell", "pwsh")) {
        throw "UDP port 8765 is owned by $($listenerProcess.Name), not the movie-mode helper."
    }

    Stop-Process `
        -Id $listener.OwningProcess `
        -Force
}

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

$deadline = [DateTime]::UtcNow.AddSeconds(10)

do {
    Start-Sleep -Milliseconds 250

    $listener = Get-NetUDPEndpoint `
        -LocalPort 8765 `
        -ErrorAction SilentlyContinue
}
while ($null -eq $listener -and [DateTime]::UtcNow -lt $deadline)

$listener = Get-NetUDPEndpoint `
    -LocalPort 8765 `
    -ErrorAction SilentlyContinue

if ($null -eq $listener) {
    throw "Agent did not start listening on UDP port 8765."
}

Write-Host "Movie Mode agent installed in per-user startup and listening on UDP port 8765."
