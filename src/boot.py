import board
import digitalio
import storage


# Web Workflow can only write files when USB mass storage is disabled.
# Hold the center button while powering on or resetting to keep the
# CIRCUITPY drive mounted for recovery.
button = digitalio.DigitalInOut(board.BTN)
button.switch_to_input(pull=digitalio.Pull.UP)

if button.value:
    storage.disable_usb_drive()

button.deinit()
