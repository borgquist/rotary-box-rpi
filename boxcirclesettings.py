from stepper import Stepper

class BoxCircleSettings:
    def __init__(self):
        self.stepper = Stepper()
        self.schedules = []
        self.nrPockets = 0
    

    def __str__(self):
        return "stepper [" + str(self.stepper) + "] schedules [" + str(self.schedules) + "] nrPockets [" + str(self.nrPockets) + "]"
