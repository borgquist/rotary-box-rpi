class LatestMove:
    def __init__(self):
        self.stepsDone = 0
        self.stepsDoneAfterIr = 0
        self.irTriggered = False
        self.timestamp = "1900-01-01 00:00:00"
        self.timeStr = ""
        self.boxOwnerPossessive = ""
        self.minutesSincePod = 0
        self.notifyNow = True

    def getDict(self):
        return self.__dict__
    def __str__(self):
            return str(self.__dict__)
