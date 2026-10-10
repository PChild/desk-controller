param(
    [Parameter(Mandatory = $true)]
    [string]$DisplayName,

    [Parameter(Mandatory = $true)]
    [int]$AgentPort,

    [Parameter(Mandatory = $true)]
    [string]$Token,

    [Parameter(Mandatory = $true)]
    [string]$ControllerOffUrl
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

$screen = [Windows.Forms.Screen]::AllScreens |
    Where-Object DeviceName -eq $DisplayName |
    Select-Object -First 1

if ($null -eq $screen) {
    throw "Display not found: $DisplayName"
}

$form = [Windows.Forms.Form]::new()
$form.BackColor = [Drawing.Color]::Black
$form.FormBorderStyle = [Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [Windows.Forms.FormStartPosition]::Manual
$form.Bounds = $screen.Bounds
$form.TopMost = $true
$form.ShowInTaskbar = $false
$form.Cursor = [Windows.Forms.Cursors]::Hand

$form.Add_Click({
    # Give immediate visual feedback while the controller closes both overlays.
    $form.Hide()

    try {
        $client = [Net.Sockets.UdpClient]::new()
        $payload = [Text.Encoding]::UTF8.GetBytes(
            $Token + ":on"
        )

        [void]$client.Send(
            $payload,
            $payload.Length,
            "127.0.0.1",
            $AgentPort
        )

        # Close the other overlay over localhost first, then synchronize the
        # ESP32 state directly. The clicked form is already hidden, so a slow
        # network response cannot delay the visible exit from movie mode.
        $request = [Net.HttpWebRequest]::Create($ControllerOffUrl)
        $request.Method = "GET"
        $request.Timeout = 3000
        $request.ReadWriteTimeout = 3000

        $response = $request.GetResponse()
        $response.Dispose()
    }
    finally {
        if ($null -ne $client) {
            $client.Dispose()
        }

        $form.Close()
    }
})

[Windows.Forms.Application]::Run($form)
