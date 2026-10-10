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
        $config.ControlMyMonitorPath
    )
)
$monitorIds = @($config.MonitorIds)
$listenPort = [int]$config.ListenPort
$token = [string]$config.Token

if (-not (Test-Path -LiteralPath $toolPath)) {
    throw "ControlMyMonitor was not found: $toolPath"
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

function Set-MonitorPower {
    param(
        [string]$MonitorId,
        [int]$PowerValue
    )

    $process = Start-Process `
        -FilePath $toolPath `
        -ArgumentList @(
            "/SetValue",
            $MonitorId,
            "D6",
            $PowerValue
        ) `
        -WindowStyle Hidden `
        -Wait `
        -PassThru

    return $process.ExitCode -eq 0
}

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
                foreach ($monitorId in $monitorIds) {
                    if (-not (Set-MonitorPower $monitorId 5)) {
                        Write-Warning (
                            "Could not put monitor in standby: " +
                            $monitorId
                        )
                    }

                    Start-Sleep -Milliseconds 250
                }

                Write-Host "Movie mode on: monitors in standby"
            }
            "on" {
                foreach ($monitorId in $monitorIds) {
                    if (-not (Set-MonitorPower $monitorId 1)) {
                        Write-Warning (
                            "Could not wake monitor: " +
                            $monitorId
                        )
                    }

                    Start-Sleep -Milliseconds 250
                }

                Write-Host "Movie mode off: monitors awake"
            }
            default {
                Write-Warning "Ignored unknown action: $action"
                continue
            }
        }
    }
}
finally {
    $udp.Dispose()
}
