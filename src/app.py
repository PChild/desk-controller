import gc
import time

import microcontroller
import wifi


try:
    from watchdog import WatchDogMode
    WATCHDOG_AVAILABLE=True

except ImportError:

    WATCHDOG_AVAILABLE=False


from desk import DeskController
from wifi_manager import WifiManager
from status_led import StatusLED



class DeskApplication:


    def __init__(self):

        self.started=time.monotonic()
        
        self.last_successful_loop = time.monotonic()

        self.led=StatusLED()

        self.led.booting()


        self.desk=DeskController()


        # Critical:
        # Never leave outputs active after boot

        self.desk.release()


        self.network=WifiManager(
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

            microcontroller.watchdog.timeout=30

            microcontroller.watchdog.mode=(
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




    def status(self):

        data = self.desk.status()

        try:
            ip = str(wifi.radio.ipv4_address)
        except Exception:
            ip = None

        data["uptime"] = int(
            time.monotonic() - self.started
        )
        
        data["last_successful_loop"] = int(
            time.monotonic()
            -
            self.last_successful_loop
        )

        data["loop_timestamp"] = (
            self.last_successful_loop
        )

        data["free_memory"] = gc.mem_free()

        data["wifi"] = wifi.radio.connected

        data["ip"] = ip

        data["hostname"] = (
            self.network.hostname
            + ".local"
        )

        return data

    def run(self):

        while True:

            self.feed_watchdog()


            try:

                self.network.poll()

                self.led.poll()


                # If we got here, the main loop succeeded
                self.last_successful_loop = (
                    time.monotonic()
                )


            except Exception as e:

                print(
                    "Fatal loop error:",
                    e
                )


                self.led.error()


                try:

                    self.desk.release()

                except Exception:

                    pass


                time.sleep(2)



            gc.collect()

            time.sleep(
                0.01
            )




def run():

    app=DeskApplication()

    app.run()