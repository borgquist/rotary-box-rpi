import subprocess
from datetime import datetime
from types import MappingProxyType
import socket
import logging

logger = logging.getLogger('podq')

class UtilityFunctions:
    
    @staticmethod
    def generateId() -> str:
        return datetime.now().strftime('%Y%m%d-%H%M%S%f-')

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
    def internetSubprocessCheck() -> bool:
        googleHostForInternetCheck = "1.1.1.1"
        try:
            output = subprocess.check_output(
                "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)
        except Exception:
            return False
        return True

    @staticmethod
    def internetSocketCheck():
        try:
            # connect to the host -- tells us if the host is actually
            # reachable
            socket.create_connection(("1.1.1.1", 53), 3)
            return True
        except OSError:
            pass
        return False
    
    def check_internet_connection():
        """ Returns True if there's a connection """

        IP_ADDRESS_LIST = [
            "1.1.1.1",  # Cloudflare
            "1.0.0.1",
            "8.8.8.8",  # Google DNS
            "8.8.4.4",
            "208.67.222.222",  # Open DNS
            "208.67.220.220"
        ]
        port = 53
        timeout = 3
        oneLost = False
        for host in IP_ADDRESS_LIST:
            try:
                socket.setdefaulttimeout(timeout)
                socket.socket(socket.AF_INET, socket.SOCK_STREAM).connect((host, port))
                # if(oneLost):
                logger.info("internet successful check for " + host)
                return True
            except socket.error:
                logger.warning("internet check failed for " + host)
                oneLost = True
                pass
        else:
            logger.warning("internet check failed for all")
            return False 


    @staticmethod
    def getWifiInfo(longVersion: bool):
        try:
            if(longVersion):
                return subprocess.check_output(['iwconfig']).decode('utf-8')
            else:
                return subprocess.check_output(['iwgetid']).decode('utf-8')
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

    