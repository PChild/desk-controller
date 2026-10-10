param(
    [string]$ConfigPath = "$PSScriptRoot\movie_mode_agent_config.psd1"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Missing configuration file: $ConfigPath"
}

$config = Import-PowerShellDataFile -LiteralPath $ConfigPath
$configDirectory = Split-Path -Parent (
    [IO.Path]::GetFullPath($ConfigPath)
)
$toolPath = [IO.Path]::GetFullPath(
    [IO.Path]::Combine(
        $configDirectory,
        $config.MultiMonitorToolPath
    )
)
$savedLayoutPath = Join-Path $configDirectory "movie_mode_monitors.cfg"
$monitorIds = @($config.MonitorIds)
$listenPort = [int]$config.ListenPort
$token = [string]$config.Token

if (-not (Test-Path -LiteralPath $toolPath)) {
    throw "MultiMonitorTool was not found: $toolPath"
}

if ($monitorIds.Count -ne 2) {
    throw "Configure exactly two MonitorIds."
}

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Configure a non-empty Token."
}

$udp = [Net.Sockets.UdpClient]::new($listenPort)
$remote = [Net.IPEndPoint]::new([Net.IPAddress]::Any, 0)

Write-Host "Movie-mode agent listening on UDP port $listenPort"
Write-Host "Press Ctrl+C to stop."

try {
    while ($true) {
        $bytes = $udp.Receive([ref]$remote)
        $message = [Text.Encoding]::UTF8.GetString($bytes)
        $separator = $message.LastIndexOf(":")

        if ($separator -lt 1) {
            Write-Warning "Ignored malformed command from $($remote.Address)"
            continue
        }

        $receivedToken = $message.Substring(0, $separator)
        $action = $message.Substring($separator + 1)

        if ($receivedToken -cne $token) {
            Write-Warning "Ignored command with invalid token from $($remote.Address)"
            continue
        }

        switch ($action) {
            "off" {
                & $toolPath /SaveConfig $savedLayoutPath

                if ($LASTEXITCODE -ne 0) {
                    Write-Warning "Could not save the monitor layout"
                    continue
                }

                & $toolPath /disable @monitorIds
                Write-Host "Movie mode on: monitors disabled"
            }
            "on" {
                if (-not (Test-Path -LiteralPath $savedLayoutPath)) {
                    Write-Warning "No saved monitor layout is available"
                    continue
                }

                & $toolPath /LoadConfig $savedLayoutPath
                Write-Host "Movie mode off: monitor layout restored"
            }
            default {
                Write-Warning "Ignored unknown action: $action"
                continue
            }
        }

        if ($LASTEXITCODE -ne 0) {
            Write-Warning "MultiMonitorTool exited with code $LASTEXITCODE"
        }
    }
}
finally {
    $udp.Dispose()
}
