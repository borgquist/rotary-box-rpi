from stepper import Stepper

class BoxCircleSettings:
    def __init__(self):
        self.stepSettings = Stepper()
        self.schedule = []
        self.nrPockets = 0
    

    def __str__(self):
        return "stepSettings [" + str(self.stepSettings) + "] schedule [" + str(self.schedule) + "] nrPockets [" + str(self.nrPockets) + "]"
