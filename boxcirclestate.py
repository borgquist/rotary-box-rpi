from latestmove import LatestMove
class BoxCircleState:
    def __init__(self):
        self.nextMove = "0"
        self.pocketsFull = 0
        self.minutesToNextMove = 0
        self.latestMove = LatestMove()
    
    def __str__(self):
        return "nextMove [" + str(self.nextMove) + "] latestMove [" + str(self.latestMove) + "] pocketsFull [" + str(self.pocketsFull) + "] minutesToNextMove [" + str(self.minutesToNextMove) +"]"
