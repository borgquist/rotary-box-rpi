class Stepper:
    def __init__(self):
        self.maxMove = 3000
        self.minMove = 2000
        self.afterTrigger = 1000
        self.chanList = []

    def getDict(self):
        return self.__dict__
        
    def __str__(self):
        return str(self.__dict__)
