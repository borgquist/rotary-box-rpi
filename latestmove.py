class LatestMove:
    def __init__(self):
        self.irTriggered = False
        self.minutesSincePod = 0
        self.stepsAfterTrigger = 0
        self.timeStr = ""
        self.timestamp = "1900-01-01 00:00:00"
        self.timestampEpoch = 0
        self.totalSteps = 0

    def getDict(self):
        return self.__dict__
    def __str__(self):
            return str(self.__dict__)
