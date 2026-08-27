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
│   ├── app.py             # Application/main loop
│   ├── desk.py            # Desk hardware interface
│   ├── button.py          # AtomS3 Lite button
│   ├── status_led.py      # RGB status LED
│   ├── wake_on_lan.py     # Wake-on-LAN magic packet sender
│   ├── wifi_manager.py    # Wi-Fi, mDNS and HTTP server
│   ├── index.html          # Web interface
│   └── lib/               # CircuitPython libraries
│
├── tools/
│   └── deploy.py          # Deploy to CIRCUITPY
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
