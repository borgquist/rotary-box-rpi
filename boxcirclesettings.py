from stepper import Stepper
import json


class BoxCircleSettings:
    stepSettings = Stepper()
    schedule = []
    nrPockets = 0
    

    def __str__(self):
        return "stepSettings [" + str(self.stepSettings) + "] schedule [" + str(self.schedule) + "] nrPockets [" + str(self.nrPockets) + "]"
