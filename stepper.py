class Stepper:
    def __init__(self):
        self.name = ""
        self.maxMove = 3000
        self.minMove = 2000
        self.afterTrigger = 1000
        self.chanList = []

    def __str__(self):
        return "name [" + str(self.name) + "] maxMove [" + str(self.maxMove) + "] minMove [" + str(self.minMove) + "] afterTrigger [" + str(self.afterTrigger) + "] chanList [" + str(self.chanList) + "]"
