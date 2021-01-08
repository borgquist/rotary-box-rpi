from stepper import Stepper
import json


class FirebaseBoxSettings:
    innerStepper = Stepper()
    outerStepper = Stepper()

    innerSchedule = []
    outerSchedule = []

    def __str__(self):
        return "innerStepper [" + str(self.innerStepper) + "] outerStepper [" + str(self.outerStepper) + "] innerSchedule [" + str(self.innerSchedule) + "] outerSchedule [" + str(self.outerSchedule) + "]"
