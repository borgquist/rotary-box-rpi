from stepper import Stepper
import json

class FirebaseBoxSettings:
    innerStepper = Stepper()
    outerStepper = Stepper()

    class Schedule:
        day = "everyday"
        hour = 7
        minute = 0
        def __str__(self):
            return "day [" + str(self.day) + "] hour [" + str(self.hour) + "] minute [" + str(self.minute) + "]"


    innerSchedule = []
    outerSchedule = []

    hostname = "hostname"
    ipAddress = "1.1.1.1"
    version = "0.0.0"

    def __str__(self):
        return "innerStepper [" + str(self.innerStepper) + "] outerStepper [" + str(self.outerStepper) + "] innerSchedule [" + str(self.innerSchedule) + "] outerSchedule [" + str(self.outerSchedule) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "]"

    def toJSON(self):
        return json.dumps(self, default=lambda o: o.__dict__, 
            sort_keys=True, indent=4)