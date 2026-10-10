import argparse
import base64
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


SRC = Path(__file__).parent.parent / "src"
SETTINGS = SRC / "settings.toml"

EXCLUDE = {
    ".git",
    ".gitignore",
    "__pycache__",
    ".DS_Store",
    "settings.toml.example",
}


def read_setting(name, default=None):

    text = SETTINGS.read_text(encoding="utf-8")
    match = re.search(
        r"^\s*" + re.escape(name) + r"\s*=\s*(?:\"([^\"]*)\"|'([^']*)'|([^#\r\n]+))",
        text,
        re.MULTILINE,
    )

    if not match:
        return default

    return next(
        value.strip()
        for value in match.groups()
        if value is not None
    )


def should_skip(path):

    return any(part in EXCLUDE for part in path.parts)


def api_request(url, password, method="GET", data=None, headers=None, timeout=15):

    auth = base64.b64encode(
        (":" + password).encode("utf-8")
    ).decode("ascii")

    request_headers = {
        "Authorization": "Basic " + auth,
    }
    request_headers.update(headers or {})

    request = Request(
        url,
        data=data,
        headers=request_headers,
        method=method,
    )

    with urlopen(request, timeout=timeout) as response:
        return response.read()


def device_url(base_url, relative, directory=False):

    path = quote(relative.as_posix(), safe="/")

    if directory and not path.endswith("/"):
        path += "/"

    return base_url + "/fs/" + path


def ensure_directories(base_url, password, files):

    directories = sorted(
        {
            parent
            for relative in files
            for parent in relative.parents
            if parent != Path(".")
        },
        key=lambda path: len(path.parts),
    )

    for directory in directories:

        try:
            api_request(
                device_url(base_url, directory, directory=True),
                password,
                method="PUT",
                data=b"",
            )
        except HTTPError as error:
            # Existing directories may be reported as conflict by some
            # CircuitPython versions.
            if error.code != 409:
                raise


def reboot_application(host, token):

    url = "http://" + host + "/api/reboot"
    deadline = time.monotonic() + 20
    last_error = None

    while time.monotonic() < deadline:

        try:
            request = Request(
                url,
                headers={"X-Deploy-Token": token},
            )

            with urlopen(request, timeout=3) as response:
                response.read()

            print("  REBOOT requested")
            return

        except (HTTPError, URLError, TimeoutError, OSError) as error:
            last_error = error
            time.sleep(1)

    raise RuntimeError(
        "Files uploaded, but the controller could not be rebooted: "
        + str(last_error)
    )


def main():

    parser = argparse.ArgumentParser(
        description="Deploy CircuitPython files over Wi-Fi"
    )
    parser.add_argument(
        "--host",
        default=None,
        help="controller hostname or IP (default: CIRCUITPY_WIFI_HOSTNAME.local)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Web Workflow port (default: setting or 8080)",
    )
    parser.add_argument(
        "--password",
        default=None,
        help="current device Web Workflow password (default: local setting)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="show files without uploading",
    )
    parser.add_argument(
        "--no-reboot",
        action="store_true",
        help="upload files without requesting a hard reset",
    )
    args = parser.parse_args()

    if not SETTINGS.exists():
        raise SystemExit("Missing src/settings.toml")

    hostname = read_setting("CIRCUITPY_WIFI_HOSTNAME", "desk")
    host = args.host or (hostname + ".local")
    port = args.port or int(read_setting("CIRCUITPY_WEB_API_PORT", "8080"))
    configured_password = read_setting("CIRCUITPY_WEB_API_PASSWORD")
    password = args.password or configured_password

    if not configured_password:
        raise SystemExit("Set CIRCUITPY_WEB_API_PASSWORD in src/settings.toml")

    files = [
        path.relative_to(SRC)
        for path in SRC.rglob("*")
        if path.is_file() and not should_skip(path.relative_to(SRC))
    ]

    # Updating code.py last prevents an early reload from interrupting the
    # rest of the upload.
    files.sort(key=lambda path: (path.name == "code.py", path.as_posix()))

    print("Source:", SRC)
    print("Device:", "http://{}:{}".format(host, port))

    for relative in files:
        print(" ", "WOULD UPLOAD" if args.dry_run else "UPLOAD", relative)

    if args.dry_run:
        return

    base_url = "http://{}:{}".format(host, port)

    try:
        ensure_directories(base_url, password, files)

        for relative in files:
            api_request(
                device_url(base_url, relative),
                password,
                method="PUT",
                data=(SRC / relative).read_bytes(),
                headers={"Content-Type": "application/octet-stream"},
                timeout=30,
            )

    except HTTPError as error:
        if error.code == 401:
            raise SystemExit("Authentication failed; check the Web Workflow password")
        if error.code == 409:
            raise SystemExit(
                "Device filesystem is read-only; power-cycle without exposing USB storage"
            )
        raise

    if not args.no_reboot:
        # The application reload sees the newly uploaded setting, while the
        # Web Workflow may still authenticate with the old setting until the
        # hard reset. These differ when rotating the password.
        reboot_application(host, configured_password)

    print("Deploy complete.")


if __name__ == "__main__":
    main()
