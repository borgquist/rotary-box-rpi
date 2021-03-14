from datetimefunctions import DateTimeFunctions
import pyrebase
import json
import logging
import time
import subprocess
from boxsettings import BoxSettings


folderPath = '/home/pi/'
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(folderPath + "logs/podq.log")
file_handler.setLevel(logging.INFO)
logger.addHandler(file_handler)


googleHostForInternetCheck = "8.8.8.8"


def haveInternet():
    try:
        output = subprocess.check_output(
            "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)
    except Exception:
        return False
    return True




class FirebaseConnection:
    cpuid = 0
    
    def __init__(self, cpuid):
        self.cpuid = cpuid
        

    configFilePath = '/home/pi/config.json'
    with open(configFilePath, 'r') as f:
        configToBeLoaded = json.load(f)
    apiKey = configToBeLoaded['apiKey']
    authDomain = configToBeLoaded['authDomain']
    databaseURL = configToBeLoaded['databaseURL']
    storageBucket = configToBeLoaded['storageBucket']

    config = {
        "apiKey": apiKey,
        "authDomain": authDomain,
        "databaseURL": databaseURL,
        "storageBucket": storageBucket
    }

    
    firebase = pyrebase.initialize_app(config)
    database = firebase.database()


    def setFirebaseValue(self, settingname, newValue, parent = None, grandparent = None, greatgrandparent = None):
        internetWasLost = False
        while(not haveInternet()):
            internetWasLost = True
            logger.info("internet is not available, sleeping 1 second")
            time.sleep(1)
        if(internetWasLost):
            logger.info("have internet connectivity")

    

        if(settingname == "timestamp"):
            self.database.child("box").child("boxes").child(self.cpuid).child(settingname).set(newValue)
            return

        if(parent is None):
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get()
        elif(grandparent is None):
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get()
        elif(greatgrandparent is None):
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get()
        else:
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(greatgrandparent).child(grandparent).child(parent).child(settingname).get()

        if(currentValue.val() == newValue):
            return # no need to update

        logMessasge = settingname
        if(parent is not None):
            logMessasge = parent + "/" + logMessasge
            if(grandparent is not None):
                logMessasge = grandparent + "/" + logMessasge
                if(greatgrandparent is not None):
                    logMessasge =  greatgrandparent + "/" + grandparent + "/" + logMessasge
        logger.info("setting [" + logMessasge + "] to [" + str(newValue) + "]")

        if(parent is None):
            self.database.child("box").child("boxes").child(self.cpuid).child(settingname).set(newValue)
        elif(grandparent is None):
            self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).set(newValue)
        elif(greatgrandparent is None):
            self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).set(newValue)
        else:
            self.database.child("box").child("boxes").child(self.cpuid).child(greatgrandparent).child(grandparent).child(parent).child(settingname).set(newValue)

        
        
    
    def setPing(self, boxSettings: BoxSettings):
        self.database.child("box").child("timestamp").child(self.cpuid).child("epoch").set(time.time())
        localTime = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
        self.database.child("box").child("timestamp").child(self.cpuid).child("local").set(localTime.strftime(DateTimeFunctions.fmt))

        return

    def getPingSeconds(self):
        pingSeconds = self.database.child("box").child("ping_seconds").get()
        if pingSeconds.val() is None:
            logging.warning("couldn't get ping_seconds")
            return 600
        logger.info("ping_seconds is: " + str(pingSeconds.val()))
        return str(pingSeconds.val())

    def getFirebaseValue(self, settingname, defaultValue = None, parent = None, grandparent = None, greatgrandparent = None):
        logMessasge = settingname
        if(parent is not None):
            logMessasge = parent + "/" + logMessasge
            if(grandparent is not None):
                logMessasge = grandparent + "/" + logMessasge
                if(greatgrandparent is not None):
                    logMessasge =  greatgrandparent + "/" + grandparent + "/" + logMessasge
        logger.info("firebase getting value for [" + logMessasge + "]")
        
        if(parent is None):
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get()
        elif(grandparent is None):
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get()
        elif(greatgrandparent is None):
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get()
        else:
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(greatgrandparent).child(grandparent).child(parent).child(settingname).get()
        
        if settingValue.val() is None:
            if defaultValue is None:
                logger.warning("getFirebaseValue for [" + settingname + "] has no default value and no current value")
                return None
            self.setFirebaseValue(settingname, defaultValue, parent, grandparent, greatgrandparent)
        
        if(greatgrandparent is not None):
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(greatgrandparent).child(grandparent).child(parent).child(settingname).get().val()
        elif(grandparent is not None):
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get().val()
        elif(parent is not None):
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get().val()
        else:
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get().val()
        
        logMessasge = settingname
        if(parent is not None):
            logMessasge = parent + "/" + logMessasge
            if(grandparent is not None):
                logMessasge = grandparent + "/" + logMessasge
                if(greatgrandparent is not None):
                    logMessasge =  greatgrandparent + "/" + grandparent + "/" + logMessasge

        logger.info("firebase setting [" + logMessasge + "] has value [" + str(returnVal) + "]")
        return returnVal


    def getBoxLatestVersion(self):
        latestVersion = self.database.child("box").child("latest_version").get()
        if latestVersion.val() is None:
            logger.warning("couldn't get latest_version")
            return "unknown"

        logger.info("latest_version is: " + str(latestVersion.val()))
        return str(latestVersion.val())
