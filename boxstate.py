class BoxState:
    cpuId = "000000"
    buttonLedOn = False
    timestamp = "1900-01-01 00:00:00"
    hostname = "hostname"
    ipAddress = "1.1.1.1"
    version = "0.0.0"
    
    
    def __str__(self):
        return "cpuId [" + str(self.cpuId) + "] buttonLedOn [" + str(self.buttonLedOn) + "] timestamp [" + str(self.timestamp) + "] hostname [" + str(self.hostname) + "] ipAddress [" + str(self.ipAddress) + "] version [" + str(self.version) + "]"
