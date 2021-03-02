class BoxState:
    def __init__(self):
        self.cpuId = "000000"
        self.buttonLedOn = False
        self.timestamp = "1900-01-01 00:00:00"
        self.hostname = "hostname"
        self.ipAddress = "1.1.1.1"
        self.version = "0.0.0"
    
    
    def __str__(self):
        return "cpuId [" + str(self.cpuId) + "] buttonLedOn [" + str(self.buttonLedOn) + "] timestamp [" + str(self.timestamp) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "] version [" + str(self.version) + "]"
