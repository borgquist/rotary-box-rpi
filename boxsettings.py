class BoxSettings:
    def __init__(self):
        self.timezone = "Europe/London"
    
    def getDict(self):
        return self.__dict__
    
    def __str__(self):
        return str(self.__dict__)
