import subprocess
from datetime import datetime
from uuid import uuid4

class UtilityFunctions:
    
    @staticmethod
    def generateId() -> str:
        return datetime.now().strftime('%Y%m-%d%H-%M%S-') + str(uuid4())

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

        