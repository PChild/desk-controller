import os
import time

import wifi
import socketpool
import mdns

from adafruit_httpserver import (
    Server,
    Response,
    JSONResponse,
)


class WifiManager:

    def __init__(self, app):

        self.app = app

        self.hostname = os.getenv(
            "CIRCUITPY_HOSTNAME",
            "desk"
        )

        self.server = None
        self.pool = None
        self.mdns_server = None

        self.last_check = 0


    def connect(self):

        self.connect_wifi()

        self.start_mdns()

        self.start_server()


    def connect_wifi(self):

        if wifi.radio.connected:

            return


        ssid = os.getenv(
            "CIRCUITPY_WIFI_SSID"
        )

        password = os.getenv(
            "CIRCUITPY_WIFI_PASSWORD"
        )


        while True:

            try:

                print(
                    "Connecting WiFi..."
                )


                wifi.radio.connect(
                    ssid,
                    password
                )


                print(
                    "Connected:",
                    wifi.radio.ipv4_address
                )


                break


            except Exception as e:

                print(
                    "WiFi failed:",
                    e
                )

                time.sleep(5)


    def start_mdns(self):

        try:

            self.mdns_server = mdns.Server(
                wifi.radio
            )

            self.mdns_server.hostname = (
                self.hostname
            )


            print(
                "mDNS:",
                self.hostname
                +
                ".local"
            )


        except Exception as e:

            print(
                "mDNS failed:",
                e
            )


    def start_server(self):

        self.pool = socketpool.SocketPool(
            wifi.radio
        )


        http_debug = (
            os.getenv(
                "HTTP_DEBUG",
                "false"
            ).lower()
            ==
            "true"
        )


        self.server = Server(
            self.pool,
            "/",
            debug=http_debug
        )


        self.routes()


        self.server.start(
            str(
                wifi.radio.ipv4_address
            ),
            80
        )


        print(
            "HTTP running"
        )


    def routes(self):

        @self.server.route("/")
        def home(request):

            with open(
                "/index.html",
                "r"
            ) as f:

                return Response(
                    request,
                    f.read(),
                    content_type="text/html"
                )


        @self.server.route(
            "/api/status"
        )
        def status(request):

            return JSONResponse(
                request,
                self.app.status()
            )


        @self.server.route(
            "/api/stand"
        )
        def stand(request):

            return self.command(
                request,
                "stand"
            )


        @self.server.route(
            "/api/stow"
        )
        def stow(request):

            return self.command(
                request,
                "stow"
            )


        @self.server.route(
            "/api/sit"
        )
        def sit(request):

            return self.command(
                request,
                "sit"
            )


        @self.server.route(
            "/api/wake"
        )
        def wake(request):

            ok, message = self.app.wake_on_lan.send(
                self.pool
            )


            return JSONResponse(
                request,
                {
                    "success": ok,
                    "message": message
                }
            )


        @self.server.route(
            "/api/movie"
        )
        def movie(request):

            return self.movie_mode(
                request,
                None
            )


        @self.server.route(
            "/api/movie/on"
        )
        def movie_on(request):

            return self.movie_mode(
                request,
                True
            )


        @self.server.route(
            "/api/movie/off"
        )
        def movie_off(request):

            return self.movie_mode(
                request,
                False
            )


        @self.server.route(
            "/api/reboot"
        )
        def reboot(request):

            expected = os.getenv(
                "CIRCUITPY_WEB_API_PASSWORD"
            )

            supplied = request.headers.get(
                "X-Deploy-Token"
            )

            if (
                not expected
                or
                supplied != expected
            ):

                return JSONResponse(
                    request,
                    {
                        "success": False,
                        "message": "Invalid deploy token"
                    },
                    status=(401, "Unauthorized")
                )


            self.app.request_reset()


            return JSONResponse(
                request,
                {
                    "success": True,
                    "message": "Reboot scheduled"
                }
            )


    def command(
        self,
        request,
        command
    ):

        ok, msg = self.app.desk.press(
            command
        )


        return JSONResponse(
            request,
            {
                "success": ok,
                "message": msg
            }
        )


    def movie_mode(
        self,
        request,
        enabled
    ):

        if enabled is None:

            ok, message = (
                self.app.movie_mode.toggle(
                    self.pool
                )
            )

        else:

            ok, message = (
                self.app.movie_mode.set_enabled(
                    self.pool,
                    enabled
                )
            )


        return JSONResponse(
            request,
            {
                "success": ok,
                "message": message,
                "movie_mode_enabled": (
                    self.app.movie_mode.enabled
                )
            }
        )


    def reconnect(self):

        print(
            "Reconnecting WiFi"
        )


        try:

            if self.server is not None:

                self.server.stop()

        except Exception:

            pass


        self.server = None
        self.pool = None
        self.mdns_server = None


        try:

            wifi.radio.stop_station()

        except Exception:

            pass


        self.connect()


    def poll(self):

        now = time.monotonic()


        if (
            now
            -
            self.last_check
            >
            10
        ):

            self.last_check = now


            if not wifi.radio.connected:

                self.reconnect()


        if self.server is not None:

            self.server.poll()
