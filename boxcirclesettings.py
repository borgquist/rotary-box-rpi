from stepper import Stepper

class BoxCircleSettings:
    def __init__(self):
        self.stepper = Stepper()
        self.schedule = []
        self.nrPockets = 0
    

    def __str__(self):
        return "stepper [" + str(self.stepper) + "] schedule [" + str(self.schedule) + "] nrPockets [" + str(self.nrPockets) + "]"
