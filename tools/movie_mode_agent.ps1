param(
    [string]$ConfigPath = "$PSScriptRoot\movie_mode_agent_config.psd1"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $ConfigPath)) {
    throw "Missing configuration file: $ConfigPath"
}

$config = Import-PowerShellDataFile -LiteralPath $ConfigPath
$blackoutDisplays = @($config.BlackoutDisplays)
$listenPort = [int]$config.ListenPort
$token = [string]$config.Token
$blackoutScript = Join-Path $PSScriptRoot "movie_mode_blackout.ps1"
$controllerOffUrl = if ($config.ControllerOffUrl) {
    [string]$config.ControllerOffUrl
}
else {
    "http://desk.local/api/movie/off"
}

if (-not (Test-Path -LiteralPath $blackoutScript)) {
    throw "Missing blackout script: $blackoutScript"
}

if ($blackoutDisplays.Count -ne 2) {
    throw "Configure exactly two BlackoutDisplays."
}

if ([string]::IsNullOrWhiteSpace($token)) {
    throw "Configure a non-empty Token."
}

$udp = [Net.Sockets.UdpClient]::new($listenPort)
$remote = [Net.IPEndPoint]::new([Net.IPAddress]::Any, 0)

Write-Host "Movie-mode agent listening on UDP port $listenPort"
Write-Host "Press Ctrl+C to stop."

$blackoutProcesses = @()

function Get-BlackoutProcesses {
    return @(
        Get-CimInstance Win32_Process |
            Where-Object {
                $_.Name -in @("powershell.exe", "pwsh.exe") -and
                $_.CommandLine -match (
                    '(?i)-File\s+"?[^\"]*' +
                    'movie_mode_blackout\.ps1'
                )
            }
    )
}

function Remove-OrphanBlackouts {
    foreach ($process in Get-BlackoutProcesses) {
        Stop-Process `
            -Id $process.ProcessId `
            -Force `
            -ErrorAction SilentlyContinue
    }
}

function Stop-Blackouts {
    foreach ($process in $script:blackoutProcesses) {
        if (-not $process.HasExited) {
            Stop-Process `
                -Id $process.Id `
                -Force `
                -ErrorAction SilentlyContinue
        }
    }

    $script:blackoutProcesses = @()
}

# Clean up overlays left behind if a previous agent was interrupted.
Remove-OrphanBlackouts

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
                Stop-Blackouts

                foreach ($displayName in $blackoutDisplays) {
                    $process = Start-Process `
                        -FilePath "powershell.exe" `
                        -ArgumentList @(
                            "-NoProfile",
                            "-ExecutionPolicy",
                            "Bypass",
                            "-WindowStyle",
                            "Hidden",
                            "-File",
                            $blackoutScript,
                            "-DisplayName",
                            $displayName,
                            "-AgentPort",
                            $listenPort,
                            "-Token",
                            $token,
                            "-ControllerOffUrl",
                            $controllerOffUrl
                        ) `
                        -WindowStyle Hidden `
                        -PassThru

                    $script:blackoutProcesses += $process
                }

                Write-Host "Movie mode on: blackouts shown"
            }
            "on" {
                Stop-Blackouts

                Write-Host "Movie mode off: blackouts closed"
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
