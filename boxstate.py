class BoxState:
    def __init__(self):
        self.cpuId = "000000"
        self.buttonLedOn = False
        self.hostname = "hostname"
        self.ipAddress = "1.1.1.1"
        self.version = "0.0.0"
        self.localTime = None  
    
    
    def __str__(self):
        return "cpuId [" + str(self.cpuId) + "] buttonLedOn [" + str(self.buttonLedOn) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "] version [" + str(self.version) + "] localTime [" + str(self.localTime) +"]"
