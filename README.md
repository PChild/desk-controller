# Desk Controller

CircuitPython project running on an [M5Stack AtomS3 Lite](https://circuitpython.org/board/m5stack_atoms3_lite/) for a TOPSKY standing desk using the [DewertOkin DH01.02](https://www.dewertokin.com/products/office/handsets/dh01/dh0102/) controller with three programmable memory positions.

The original desk handset remains connected and fully usable. The AtomS3 Lite provides an additional network interface for controlling the three saved positions.

## Hardware

### AtomS3 Lite → desk

| AtomS3 Lite | Desk   | Function       |
| ----------- | ------ | -------------- |
| `D5`        | Line A | Control line A |
| `D6`        | Line B | Control line B |
| `D7`        | Line C | Control line C |
| `GND`       | GND    | Common ground  |

The ESP32 emulates handset button presses by pulling the control lines LOW. The lines are normally left high-impedance.

### Command encoding

| Command |  A |  B |  C |
| ------- | -: | -: | -: |
| Stand   |  1 |  0 |  0 |
| Stow    |  1 |  1 |  0 |
| Sit     |  0 |  1 |  0 |
| Idle    |  1 |  1 |  1 |

## Project structure

```text
desk-controller/
├── src/
│   ├── code.py            # CircuitPython entry point
│   ├── boot.py            # OTA filesystem and USB recovery setup
│   ├── app.py             # Application/main loop
│   ├── desk.py            # Desk hardware interface
│   ├── button.py          # AtomS3 Lite button
│   ├── movie_mode.py      # Windows movie-mode command sender
│   ├── status_led.py      # RGB status LED
│   ├── wake_on_lan.py     # Wake-on-LAN magic packet sender
│   ├── wifi_manager.py    # Wi-Fi, mDNS and HTTP server
│   ├── index.html          # Web interface
│   └── lib/               # CircuitPython libraries
│
├── tools/
│   ├── deploy.py          # Deploy over USB
│   └── deploy_wifi.py     # Deploy over Wi-Fi
├── settings.toml.example
├── requirements.txt
└── README.md
```

## Web interface

The controller is normally available at:

```text
http://desk.local
```

API endpoints:

```text
GET /api/status
GET /api/stand
GET /api/stow
GET /api/sit
GET /api/wake
GET /api/movie
GET /api/movie/on
GET /api/movie/off
GET /api/reboot            # requires X-Deploy-Token
```

## Reliability

The controller:

* Automatically reconnects to Wi-Fi.
* Provides `desk.local` through mDNS.
* Uses a 30-second hardware watchdog.
* Releases desk outputs after errors.
* Prevents repeated commands with a five-second lockout.
* Keeps the AtomS3 Lite LED normally off.
* Uses the LED to indicate startup and controller status.

The original desk handset continues to work if the ESP32 is powered off or disconnected.

## Center button Wake-on-LAN

Pressing the AtomS3 Lite center button or selecting **Wake PC** in the web
interface sends a Wake-on-LAN magic packet. Set the target computer's MAC
address in `src/settings.toml`:

```toml
WOL_MAC_ADDRESS="AA:BB:CC:DD:EE:FF"
WOL_BROADCAST_ADDRESS="255.255.255.255"
WOL_PORT=9
```

The broadcast address and port are optional; the defaults shown above work on
many local networks. If the global broadcast is blocked by your router, use the
subnet broadcast address instead (for example, `192.168.1.255`). Wake-on-LAN
must also be enabled in the target computer's firmware and network-adapter
settings.

## Movie mode

The **Movie Mode** web button covers two configured Windows displays with
borderless, always-on-top black windows. The ESP32 sends a token-protected UDP
command to a Windows helper. Windows keeps both displays attached, so windows
and icons do not move to the remaining display. Exiting movie mode closes both
blackouts immediately. Clicking either blacked-out display also exits movie
mode, closes both overlays, and resets the ESP32 toggle state.

1. Copy `tools/movie_mode_agent_config.psd1.example` to
   `tools/movie_mode_agent_config.psd1` and set the two Windows display names,
   UDP port, and a private token.
4. Add the matching computer address, port, and token to `src/settings.toml`:

```toml
MOVIE_MODE_HOST="192.168.1.151"
MOVIE_MODE_PORT=8765
MOVIE_MODE_TOKEN="use-the-same-private-token-here"
```

5. Allow inbound UDP port 8765 through Windows Firewall on the private network,
   then start the helper while signed in:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools\movie_mode_agent.ps1
```

For reliable recovery, a Stream Deck button can call either explicit endpoint:

```text
http://desk.local/api/movie/on   # enter movie mode; monitors go to standby
http://desk.local/api/movie/off  # leave movie mode; monitors turn on
```

The regular `/api/movie` endpoint toggles the current controller state. The
controller's state resets to off after an ESP32 reboot, so use the explicit
`/api/movie/off` endpoint whenever the displayed state is uncertain.

## Deploying code

`tools/deploy.py` deploys the contents of `src/` to the AtomS3 Lite's `CIRCUITPY` drive.

It is intended to be run from the project root:

```text
python tools/deploy.py
```

The deployment script:

* Copies only files intended for the ESP32.
* Does not deploy development files such as `tools/`, `stubs/`, `.git/`, or `settings.toml.example`.
* Removes files on the device that are no longer present in `src/`.
* Can detect unchanged files and avoid rewriting them.

### Dry run

Use `--dry-run` to see what would change without modifying the device:

```text
python tools/deploy.py --dry-run
```

This is useful for checking the deployment before actually changing the ESP32.

A typical workflow is:

```text
Edit in VS Code
      ↓
python tools/deploy.py --dry-run
      ↓
Review changes
      ↓
python tools/deploy.py
      ↓
ESP32 reloads
```


## Development


Edit files under `src/` and run the deployment script to synchronize files to the AtomS3 Lite.

Keep Wi-Fi credentials in `settings.toml`. Do not commit the real `settings.toml` to Git.

## Updating over Wi-Fi

The controller uses CircuitPython Web Workflow on port 8080 for authenticated
file uploads. Add these settings to `src/settings.toml`:

```toml
CIRCUITPY_WIFI_HOSTNAME="desk"
CIRCUITPY_WEB_API_PASSWORD="use-a-unique-random-password"
CIRCUITPY_WEB_API_PORT=8080
CIRCUITPY_WEB_INSTANCE_NAME="Desk Controller"
```

Web Workflow uses unencrypted HTTP on the local network. Use a unique password,
do not reuse an important password, and do not expose these ports to the
internet.

Enabling OTA requires one final USB deployment and a power cycle:

```text
python tools/deploy.py
```

After the ESP32 restarts, its USB `CIRCUITPY` drive normally stays hidden so the
Web Workflow can write to the filesystem. Future code and settings updates can
then be deployed with:

```text
python tools/deploy_wifi.py --dry-run
python tools/deploy_wifi.py
```

The Wi-Fi deploy uploads all files from `src/`, writes `code.py` last, and asks
the controller for a hard reset so changes to `settings.toml` take effect. Use
`--host 192.168.1.123` if mDNS is unavailable. If you are changing the Web
Workflow password, pass the password currently on the device with
`--password CURRENT_PASSWORD` for that deployment.

For USB recovery, hold the AtomS3 Lite center button while powering it on or
resetting it. The `CIRCUITPY` drive will remain available for that boot. Release
the button and power-cycle again to return to Wi-Fi updates.

CircuitPython's browser editor is also available at `http://desk.local:8080/`;
use a blank username and the Web Workflow password.
