param(
    [Parameter(Mandatory = $true)]
    [string]$DisplayName
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
    try {
        $client = [Net.WebClient]::new()
        [void]$client.DownloadString(
            "http://desk.local/api/movie/off"
        )
    }
    finally {
        if ($null -ne $client) {
            $client.Dispose()
        }

        $form.Close()
    }
})

[Windows.Forms.Application]::Run($form)
