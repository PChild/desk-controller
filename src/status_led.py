import board
import neopixel


class StatusLED:


    def __init__(self):

        try:

            self.pixel = neopixel.NeoPixel(
                board.NEOPIXEL,
                1,
                brightness=0.2,
                auto_write=True
            )

            self.available=True

        except Exception as e:

            print(
                "LED unavailable:",
                e
            )

            self.available=False



    def set(self, color):

        if not self.available:

            return


        try:

            self.pixel[0]=color


        except Exception:

            pass



    def off(self):

        self.set(
            (0,0,0)
        )



    def booting(self):

        self.set(
            (0,0,255)
        )



    def connected(self):

        self.set(
            (0,255,0)
        )



    def wifi_retry(self):

        self.set(
            (255,150,0)
        )



    def error(self):

        self.set(
            (255,0,0)
        )