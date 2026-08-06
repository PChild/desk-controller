import os
import time

import wifi
import socketpool
import mdns

from adafruit_httpserver import (
    Server,
    Response,
    JSONResponse
)


class WifiManager:


    def __init__(self, app):

        self.app = app

        self.hostname = os.getenv(
            "CIRCUITPY_HOSTNAME",
            "desk"
        )

        self.server = None
        self.mdns = None

        self.pool = None

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
                    "Connected"
                )

                print(
                    "IP:",
                    wifi.radio.ipv4_address
                )


                break


            except Exception as e:

                print(
                    "WiFi failed:",
                    e
                )

                if self.app.led:

                    self.app.led.wifi_retry()


                time.sleep(5)




    def start_mdns(self):

        try:

            self.mdns = mdns.Server(
                wifi.radio
            )


            self.mdns.hostname = (
                self.hostname
            )


            self.mdns.advertise_service(
                "_http",
                "_tcp",
                80
            )


            print(
                "mDNS:",
                self.hostname + ".local"
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


        self.server = Server(
            self.pool,
            "/",
            debug=True
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



    def command(
        self,
        request,
        command
    ):

        ok,msg = self.app.desk.press(
            command
        )


        return JSONResponse(
            request,
            {
                "success": ok,
                "message": msg
            }
        )



    def reconnect(self):

        print(
            "Reconnecting WiFi"
        )


        try:

            if self.server:

                self.server.stop()


        except Exception:

            pass


        self.server = None


        self.connect()


        if self.app.led:

            self.app.led.connected()



    def poll(self):

        now = time.monotonic()


        if now - self.last_check > 10:

            self.last_check = now


            if not wifi.radio.connected:

                self.reconnect()



        if self.server:

            self.server.poll()