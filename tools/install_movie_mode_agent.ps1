$ErrorActionPreference = "Stop"

$agentPath = Join-Path $PSScriptRoot "movie_mode_agent.ps1"
$configPath = Join-Path $PSScriptRoot "movie_mode_agent_config.psd1"
$pidFile = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "desk_controller_movie_mode.pid"

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

if (Test-Path -LiteralPath $pidFile) {
    $existingPid = [int](
        Get-Content `
            -LiteralPath $pidFile `
            -ErrorAction SilentlyContinue
    )

    $existingProcess = Get-Process `
        -Id $existingPid `
        -ErrorAction SilentlyContinue

    if (
        $null -ne $existingProcess -and
        $existingProcess.Name -in @("powershell", "pwsh")
    ) {
        Stop-Process `
            -Id $existingPid `
            -Force

        $existingProcess.WaitForExit(5000)
    }

    Remove-Item `
        -LiteralPath $pidFile `
        -Force `
        -ErrorAction SilentlyContinue
}

$process = Start-Process `
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
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 2

if ($process.HasExited) {
    throw "Agent exited during startup with code $($process.ExitCode)."
}

Write-Host "Movie Mode agent installed in per-user startup and listening on UDP port 8765."
