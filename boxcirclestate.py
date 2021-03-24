from latestmove import LatestMove
class BoxCircleState:
    def __init__(self):
        self.nextMove = "0"
        self.nextMoveInEpoch = "0"
        self.pocketsFull = 0
        self.latestMove = LatestMove()
    
    def getDict(self):
        return self.__dict__
    
    def __str__(self):
        return str(self.__dict__)
