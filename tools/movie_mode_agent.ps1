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
$msigdPath = [string]$config.MsigdPath
$brightnessMonitors = @($config.BrightnessMonitors)
$movieBrightness = if ($null -ne $config.MovieBrightness) {
    [int]$config.MovieBrightness
}
else {
    0
}
$brightnessStateFile = Join-Path `
    ([IO.Path]::GetTempPath()) `
    "desk_controller_movie_brightness.json"
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

if (
    -not [string]::IsNullOrWhiteSpace($msigdPath) -and
    -not (Test-Path -LiteralPath $msigdPath)
) {
    throw "msigd was not found: $msigdPath"
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

function Set-MovieBrightness {
    if (
        [string]::IsNullOrWhiteSpace($msigdPath) -or
        $brightnessMonitors.Count -eq 0
    ) {
        return
    }

    if (-not (Test-Path -LiteralPath $brightnessStateFile)) {
        $saved = [ordered]@{}

        foreach ($monitor in $brightnessMonitors) {
            try {
                $output = & $msigdPath `
                    --monitor $monitor `
                    --numeric `
                    --filter brightness `
                    --query 2>&1

                if ($LASTEXITCODE -ne 0) {
                    throw "msigd query exited with code $LASTEXITCODE"
                }

                $match = [regex]::Match(
                    ($output -join "`n"),
                    '(?im)^\s*brightness\s*:\s*(\d+)'
                )

                if (-not $match.Success) {
                    throw "brightness was not present in msigd output"
                }

                $saved[[string]$monitor] = [int]$match.Groups[1].Value
            }
            catch {
                Write-Warning (
                    "Could not read brightness for monitor ${monitor}: " +
                    $_.Exception.Message
                )
            }
        }

        if ($saved.Count -gt 0) {
            $saved |
                ConvertTo-Json -Compress |
                Set-Content -LiteralPath $brightnessStateFile -Encoding UTF8
        }
    }

    foreach ($monitor in $brightnessMonitors) {
        try {
            $process = Start-Process `
                -FilePath $msigdPath `
                -ArgumentList @(
                    "--monitor",
                    $monitor,
                    "--brightness",
                    $movieBrightness
                ) `
                -NoNewWindow `
                -Wait `
                -PassThru

            if ($process.ExitCode -ne 0) {
                throw "msigd exited with code $($process.ExitCode)"
            }
        }
        catch {
            Write-Warning (
                "Could not dim monitor ${monitor}: " +
                $_.Exception.Message
            )
        }
    }
}

function Restore-MonitorBrightness {
    if (
        [string]::IsNullOrWhiteSpace($msigdPath) -or
        -not (Test-Path -LiteralPath $brightnessStateFile)
    ) {
        return
    }

    try {
        $saved = Get-Content -LiteralPath $brightnessStateFile -Raw |
            ConvertFrom-Json
        $restored = $true

        foreach ($property in $saved.PSObject.Properties) {
            try {
                $process = Start-Process `
                    -FilePath $msigdPath `
                    -ArgumentList @(
                        "--monitor",
                        [int]$property.Name,
                        "--brightness",
                        [int]$property.Value
                    ) `
                    -NoNewWindow `
                    -Wait `
                    -PassThru

                if ($process.ExitCode -ne 0) {
                    throw "msigd exited with code $($process.ExitCode)"
                }
            }
            catch {
                $restored = $false
                Write-Warning (
                    "Could not restore brightness for monitor " +
                    $property.Name +
                    ": " +
                    $_.Exception.Message
                )
            }
        }

        if ($restored) {
            Remove-Item -LiteralPath $brightnessStateFile -Force
        }
    }
    catch {
        Write-Warning (
            "Could not restore saved monitor brightness: " +
            $_.Exception.Message
        )
    }
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

                Set-MovieBrightness

                Write-Host "Movie mode on: blackouts shown"
            }
            "on" {
                Stop-Blackouts
                Restore-MonitorBrightness

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
    Stop-Blackouts
    Restore-MonitorBrightness
    $udp.Dispose()
}
