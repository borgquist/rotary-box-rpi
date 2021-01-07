 class Stepper:
        maxMove = 3000
        minMove = 2000
        afterTrigger = 1000
        def __str__(self):
            return "maxMove [" + str(self.maxMove) + "] minMove [" + str(self.minMove) + "] afterTrigger [" + str(self.afterTrigger) + "]"