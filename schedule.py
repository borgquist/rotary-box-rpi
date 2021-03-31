class Schedule:
    def __init__(self):
        self.day = "everyday"
        self.dayType = ""
        self.hour = 7
        self.minute = 0
   
    def getDict(self):
        return self.__dict__

    def __str__(self):
        return str(self.__dict__)
