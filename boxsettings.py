from stepper import Stepper
import json


class FirebaseBoxSettings:
    innerStepper = Stepper()
    outerStepper = Stepper()

    innerSchedule = []
    outerSchedule = []

    hostname = "hostname"
    ipAddress = "1.1.1.1"
    version = "0.0.0"

    def __str__(self):
        return "innerStepper [" + str(self.innerStepper) + "] outerStepper [" + str(self.outerStepper) + "] innerSchedule [" + str(self.innerSchedule) + "] outerSchedule [" + str(self.outerSchedule) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "]"

    def toJSON(self):
        return {
                "innerSchedule": self.innerSchedule,
                "outerSchedule": self.outerSchedule,
                "hostname": self.hostname,
                "ipAddress": self.ipAddress,
                "version": self.version
                }
