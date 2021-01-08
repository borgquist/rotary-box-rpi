class FirebaseBoxState:
    cpuId = "000000"
    buttonLedOn = False
    timestamp = "1900-01-01 00:00:00"
    nextMoveInner = "0"
    nextMoveOuter = "0"
    hostname = "hostname"
    ipAddress = "1.1.1.1"
    version = "0.0.0"

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
        return "cpuId [" + str(self.cpuId) + "] buttonLedOn [" + str(self.buttonLedOn) + "] timestamp [" + str(self.timestamp) + "] nextMoveInner [" + str(self.nextMoveInner) + "] nextMoveOuter [" + str(self.nextMoveOuter) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "] version [" + str(self.version) + "]"
