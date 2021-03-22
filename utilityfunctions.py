import subprocess
from datetime import datetime
from types import MappingProxyType
from uuid import uuid4

class UtilityFunctions:
    
    @staticmethod
    def generateId() -> str:
        return datetime.now().strftime('%Y%m%d-%H%M%S-') + str(uuid4())

    @staticmethod
    def getserial() -> str:
        cpuserial = "123456789123456789"
        try:
            f = open('/proc/cpuinfo', 'r')
            for line in f:
                if line[0:6] == 'Serial':
                    cpuserial = line[10:26].replace('0', '')
            f.close()
        except:
            cpuserial = "ERROR000000000"
        return cpuserial

    @staticmethod
    def haveInternet() -> bool:
        googleHostForInternetCheck = "8.8.8.8"
        try:
            output = subprocess.check_output(
                "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)
        except Exception:
            return False
        return True

    @staticmethod
    def getWifiInfo():
        try:
            return subprocess.check_output(['iwconfig']).decode('utf-8')
        except Exception as err:
            return(str(err))
        
        
            
    
    @staticmethod
    def getNumberFromVersion(boxVersion: str):
        l = [int(x, 10) for x in boxVersion.split('.')]
        l.reverse()
        return sum(x * (100 ** i) for i, x in enumerate(l))


    @staticmethod
    def versionIsLessThanServer(boxVersion: str, serverVersion: str) -> bool:
        boxNumber = UtilityFunctions.getNumberFromVersion(boxVersion)
        serverNumber = UtilityFunctions.getNumberFromVersion(serverVersion)
        restartNeeded = boxNumber < serverNumber
        return restartNeeded

    