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

function Invoke-MonitorCommand {
    param(
        [string]$Command,
        [string]$MonitorId
    )

    $process = Start-Process `
        -FilePath $toolPath `
        -ArgumentList @($Command, $MonitorId) `
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
                    if (-not (Invoke-MonitorCommand "/disable" $monitorId)) {
                        Write-Warning (
                            "Could not disable monitor: " +
                            $monitorId
                        )
                    }

                    # Display configuration changes are asynchronous. Let each
                    # one settle before changing the next monitor.
                    Start-Sleep -Seconds 3
                }

                Write-Host "Movie mode on: monitors disabled"
            }
            "on" {
                $displaySwitch = Join-Path (
                    $env:SystemRoot
                ) "System32\DisplaySwitch.exe"

                Start-Process `
                    -FilePath $displaySwitch `
                    -ArgumentList "/extend" `
                    -WindowStyle Hidden `
                    -Wait

                # /extend rediscovers both detached displays. On this system,
                # the center becomes active immediately while the left display
                # needs one explicit enable after its ID reappears.
                Start-Sleep -Seconds 10

                if (-not (Invoke-MonitorCommand "/enable" $monitorIds[0])) {
                    Write-Warning (
                        "Could not enable monitor: " +
                        $monitorIds[0]
                    )
                }

                Write-Host "Movie mode off: monitors enabled"
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
