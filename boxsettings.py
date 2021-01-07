from stepper import Stepper

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

    def __str__(self):
        return "innerStepper [" + str(self.innerStepper) + "] outerStepper [" + str(self.outerStepper) + "] innerSchedule [" + str(self.innerSchedule) + "] outerSchedule [" + str(self.outerSchedule) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "]"
