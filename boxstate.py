class FirebaseBoxState:
    buttonLedOn = False
    version = "0.0.0"
    timestamp = "1900-01-01 00:00:00"
    nextMoveInner = "0"
    nextMoveOuter = "0"
    cpuId = ""

    class LatestMove:
        stepsDone = 0
        stepsDoneAfterIr = 0
        irTriggered = False
        timestamp = "1900-01-01 00:00:00"

        def __str__(self):
            return "stepsDone [" + str(self.stepsDone) + "] stepsDoneAfterIr [" + str(self.stepsDoneAfterIr) + "] irTriggered [" + str(self.irTriggered) + "] timestamp [" + str(self.timestamp) + "] latestMoveInner [" + str(self.latestMoveInner) +"] latestMoveOuter [" + str(self.latestMoveOuter) +"]"

    latestMoveOuter = LatestMove()
    latestMoveInner = LatestMove()

    def __str__(self):
        return "buttonLedOn [" + str(self.buttonLedOn) + "] version [" + str(self.version) + "] timestamp [" + str(self.timestamp) + "] nextMoveInner [" + str(self.nextMoveInner) + "] nextMoveOuter [" + str(self.nextMoveOuter) + "] cpuId [" + str(cpuId) + "]"
