import gc
import time

import microcontroller
import wifi


try:
    from watchdog import WatchDogMode

    WATCHDOG_AVAILABLE = True

except ImportError:

    WATCHDOG_AVAILABLE = False


from button import CenterButton
from desk import DeskController
from status_led import StatusLED
from wifi_manager import WifiManager


class DeskApplication:


    def __init__(self):

        self.started = time.monotonic()

        self.last_successful_loop = (
            self.started
        )


        self.led = StatusLED()

        self.button = CenterButton()

        self.led.booting()


        self.desk = DeskController()


        # Critical:
        # Never leave outputs active after boot.

        self.desk.release()


        self.network = WifiManager(
            self
        )


        self.enable_watchdog()


        try:

            self.network.connect()

            self.led.startup_ok()


        except Exception as e:

            print(
                "Network startup failed:",
                e
            )

            self.led.wifi_retry()



    def enable_watchdog(self):

        if not WATCHDOG_AVAILABLE:

            return


        try:

            microcontroller.watchdog.timeout = 30

            microcontroller.watchdog.mode = (
                WatchDogMode.RESET
            )


            print(
                "Watchdog enabled"
            )


        except Exception as e:

            print(
                "Watchdog error:",
                e
            )



    def feed_watchdog(self):

        if WATCHDOG_AVAILABLE:

            try:

                microcontroller.watchdog.feed()

            except Exception:

                pass



    def is_healthy(self):

        return (
            time.monotonic()
            -
            self.last_successful_loop
            <
            5
        )



    def status(self):

        data = self.desk.status()

        now = time.monotonic()


        try:

            ip = str(
                wifi.radio.ipv4_address
            )

        except Exception:

            ip = None


        data["uptime"] = int(
            now
            -
            self.started
        )


        data["free_memory"] = (
            gc.mem_free()
        )


        data["wifi"] = (
            wifi.radio.connected
        )


        data["ip"] = ip


        data["hostname"] = (
            self.network.hostname
            +
            ".local"
        )


        data["healthy"] = (
            self.is_healthy()
        )


        data["last_successful_loop"] = int(
            self.last_successful_loop
            -
            self.started
        )


        data["loop_age"] = (
            now
            -
            self.last_successful_loop
        )


        return data



    def poll_button(self):

        if self.button.pressed():

            self.led.show_status(
                self.is_healthy(),
                wifi.radio.connected
            )



    def run(self):

        while True:

            self.feed_watchdog()


            try:

                self.poll_button()


                self.network.poll()


                self.led.poll()


                # If we reached this point,
                # the main application loop
                # completed successfully.

                self.last_successful_loop = (
                    time.monotonic()
                )


            except Exception as e:

                print(
                    "Fatal loop error:",
                    e
                )


                try:

                    self.desk.release()

                except Exception:

                    pass


                self.led.error()


                # Allow the application to continue
                # while the watchdog remains active.

                time.sleep(2)


            gc.collect()


            time.sleep(
                0.01
            )



def run():

    app = DeskApplication()

    app.run()