class BoxCircleState:
    nextMove = "0"
    pocketsFull = 0
    

    class LatestMove:
        stepsDone = 0
        stepsDoneAfterIr = 0
        irTriggered = False
        timestamp = "1900-01-01 00:00:00"

        def __str__(self):
            return "stepsDone [" + str(self.stepsDone) + "] stepsDoneAfterIr [" + str(self.stepsDoneAfterIr) + "] irTriggered [" + str(self.irTriggered) + "] timestamp [" + str(self.timestamp) + "]"

    latestMove = LatestMove()
    
    def __str__(self):
        return "nextMove [" + str(self.nextMove) + "] latestMove [" + str(self.latestMove) + "] pocketsFull [" + str(self.pocketsFull) + "]"
