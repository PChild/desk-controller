import os
import time

import board
import neopixel


class StatusLED:


    def __init__(self):

        self.startup_display_time = int(
            os.getenv(
                "LED_STARTUP_SECONDS",
                "120"
            )
        )


        self.pixel = neopixel.NeoPixel(
            board.NEOPIXEL,
            1,
            brightness=0.2,
            auto_write=True
        )


        self.start_time = None


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

        self.start_time = time.monotonic()



    def poll(self):

        if self.start_time is None:

            return


        elapsed = (
            time.monotonic()
            -
            self.start_time
        )


        if elapsed >= self.startup_display_time:

            self.off()

            self.start_time = None



    def wifi_retry(self):

        self.pixel[0] = (
            255,
            100,
            0
        )



    def connected(self):

        self.pixel[0] = (
            0,
            255,
            0
        )



    def error(self):

        self.pixel[0] = (
            255,
            0,
            0
        )



    def off(self):

        self.pixel[0] = (
            0,
            0,
            0
        )