class LatestMove:
    def __init__(self):
        self.stepsDone = 0
        self.stepsDoneAfterIr = 0
        self.irTriggered = False
        self.timestamp = "1900-01-01 00:00:00"

    def __str__(self):
            return "stepsDone [" + str(self.stepsDone) + "] stepsDoneAfterIr [" + str(self.stepsDoneAfterIr) + "] irTriggered [" + str(self.irTriggered) + "] timestamp [" + str(self.timestamp) + "]"
