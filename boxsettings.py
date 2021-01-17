from stepper import Stepper
import json


class FirebaseBoxSettings:
    innerStepper = Stepper()
    outerStepper = Stepper()

    scheduleInner = []
    scheduleOuter = []
    innerPockets = 0
    outerPockets = 0

    def __str__(self):
        return "innerPockets [" + str(self.innerPockets) + "] outerPockets [" + str(self.outerPockets) + "] innerStepper [" + str(self.innerStepper) + "] outerStepper [" + str(self.outerStepper) + "] scheduleInner [" + str(self.scheduleInner) + "] scheduleOuter [" + str(self.scheduleOuter) + "]"
