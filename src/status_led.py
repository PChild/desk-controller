import os
import time

import board
import neopixel


class StatusLED:

    def __init__(self):

        self.startup_seconds = int(
            os.getenv(
                "LED_STARTUP_SECONDS",
                "30"
            )
        )

        self.status_seconds = int(
            os.getenv(
                "LED_STATUS_SECONDS",
                "10"
            )
        )

        self.pixel = neopixel.NeoPixel(
            board.NEOPIXEL,
            1,
            brightness=0.2,
            auto_write=True
        )

        self.display_until = None

        self.off()


    def booting(self):

        self.pixel[0] = (
            255,
            100,
            0
        )


    def startup_ok(self):

        self.pixel[0] = (
            0,
            255,
            0
        )

        self.display_until = (
            time.monotonic()
            +
            self.startup_seconds
        )


    def show_status(self, healthy, wifi_connected):

        if healthy and wifi_connected:

            self.pixel[0] = (
                0,
                255,
                0
            )

        elif not wifi_connected:

            self.pixel[0] = (
                255,
                150,
                0
            )

        else:

            self.pixel[0] = (
                255,
                0,
                0
            )

        self.display_until = (
            time.monotonic()
            +
            self.status_seconds
        )


    def poll(self):

        if self.display_until is None:

            return

        if time.monotonic() >= self.display_until:

            self.off()

            self.display_until = None


    def wifi_retry(self):

        # Don't leave this permanently illuminated.
        pass


    def connected(self):

        # Used only for compatibility with existing code.
        pass


    def error(self):

        self.pixel[0] = (
            255,
            0,
            0
        )

        self.display_until = (
            time.monotonic()
            +
            self.status_seconds
        )


    def off(self):

        self.pixel[0] = (
            0,
            0,
            0
        )