import json

class Commands:
    def __init__(self):
        self.latestTimestamp = 0
        self.moveNow_innerCircle = False
        self.moveNow_outerCircle = False
        self.doRestart = False
        self.ping = False
        self.setButtonLed = False
        self.setPocketsFull_innerCircle = False
        self.setPocketsFull_outerCircle = False  
    
    def getDict(self):
        return self.__dict__
    
    def __str__(self):
        return str(self.__dict__)
