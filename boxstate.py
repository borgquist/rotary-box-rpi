class BoxState:
    def __init__(self):
        self.cpuId = "000000"
        self.buttonLedOn = False
        self.hostname = "hostname"
        self.ipAddress = "1.1.1.1"
        self.version = "0.0.0"
        self.localTime = None  
    
    def getDict(self):
        return self.__dict__
    
    def __str__(self):
        return str(self.__dict__)
