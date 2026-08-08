import board
import digitalio


class CenterButton:

    def __init__(self):

        self.button = digitalio.DigitalInOut(
            board.BTN
        )

        self.button.switch_to_input(
            pull=digitalio.Pull.UP
        )

        self.last_state = (
            self.button.value
        )


    def pressed(self):

        current_state = (
            self.button.value
        )


        # Detect a released -> pressed transition.
        # The AtomS3 Lite button is active-low.

        pressed = (
            self.last_state
            and not current_state
        )


        self.last_state = current_state


        return pressed


    def value(self):

        return self.button.value


    def deinit(self):

        self.button.deinit()