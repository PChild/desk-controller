import time

import board
import digitalio


PRESS_TIME = 0.12

LOCKOUT_TIME = 5


class DeskController:

    DESK_COMMANDS = {

        "stand": (0,0,1),

        "stow": (1,0,1),

        "sit": (1,0,0)

    }


    def __init__(self):

        self.pins=[]

        for pin in [

            board.D5,

            board.D6,

            board.D7

        ]:

            io=digitalio.DigitalInOut(pin)

            io.direction=digitalio.Direction.INPUT

            self.pins.append(io)

        self.last_command=None

        self.last_time=0



    def set_lines(self,state):

        for io,value in zip(self.pins,state):

            if value:

                io.direction=digitalio.Direction.INPUT

            else:

                io.direction=digitalio.Direction.OUTPUT

                io.value=False



    def release(self):

        self.set_lines((1,1,1))



    def remaining_lockout(self):

        remain=LOCKOUT_TIME-(time.monotonic()-self.last_time)

        return max(0,int(remain))



    def press(self,name):

        if name not in self.DESK_COMMANDS:

            return False,"Unknown command"


        if self.remaining_lockout():

            return False,"Desk busy"


        print("Desk:",name)

        self.set_lines(

            self.DESK_COMMANDS[name]

        )

        time.sleep(PRESS_TIME)

        self.release()

        self.last_command=name

        self.last_time=time.monotonic()

        return True,"Sent "+name



    def status(self):

        return {

            "last_command":self.last_command,

            "lockout_seconds":self.remaining_lockout(),

            "locked":self.remaining_lockout()>0

        }