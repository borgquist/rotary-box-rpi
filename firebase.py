from utilityfunctions import UtilityFunctions
from datetimefunctions import DateTimeFunctions
import pyrebase
import json
import logging
import time
import subprocess
from boxsettings import BoxSettings


logger = logging.getLogger('podq')



class FirebaseConnection:

    def __init__(self, cpuid, config):
        self.configFilePath = config
        self.cpuid = cpuid
        print("cpuid " + str(cpuid) + " configFilePath " + self.configFilePath)
            

        
        with open(self.configFilePath, 'r') as f:
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
    
        self.firebase = pyrebase.initialize_app(config)
        self.database = self.firebase.database()

    def setFirebaseValue(self, settingname, newValue, parent = None, grandparent = None, greatgrandparent = None):
        while(not UtilityFunctions.internetSubprocessCheck()):
            logger.info("internet is not available, sleeping 1 second")
            time.sleep(1)
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

    def getFirebaseValue(self, settingname, defaultValue = None, parent = None, grandparent = None, greatgrandparent = None):
        logMessasge = settingname
        if(parent is not None):
            logMessasge = parent + "/" + logMessasge
            if(grandparent is not None):
                logMessasge = grandparent + "/" + logMessasge
                if(greatgrandparent is not None):
                    logMessasge =  greatgrandparent + "/" + grandparent + "/" + logMessasge
        
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
                logger.warning("[" + settingname + "] has no default value and no current value")
                return None
            logger.info("[" + settingname + "] value was none, updating it to defaultValue [" + str(defaultValue) + "] for [" + logMessasge + "]")
            self.setFirebaseValue(settingname, defaultValue, parent, grandparent, greatgrandparent)
            return defaultValue

        logger.info("firebase setting [" + logMessasge + "] has value [" + str(settingValue.val()) + "]")
        return settingValue.val()

    def setPing(self, boxSettings: BoxSettings):
        self.database.child("box").child("timestamp").child(self.cpuid).child("epoch").set(time.time())
        localTime = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
        self.database.child("box").child("timestamp").child(self.cpuid).child("local").set(localTime.strftime(DateTimeFunctions.fmt))
        logger.info("updating timestamp to: " + localTime.strftime(DateTimeFunctions.fmt))

    def getPingSeconds(self) -> int:
        pingSeconds = self.database.child("box").child("ping_seconds").get()
        if pingSeconds.val() is None:
            logging.warning("couldn't get ping_seconds")
            return 600
        logger.info("ping_seconds is: " + str(pingSeconds.val()))
        return int(pingSeconds.val())

    def setInternetCheckTimestamp(self):
        timestamp = time.time()
        self.database.child("box").child("internet_check").set(timestamp)
        logger.info("updating internet_check to: " + str(timestamp))

    def getInternetCheckTimestamp(self) -> int:
        internet_check = self.database.child("box").child("internet_check").get()
        if internet_check.val() is None:
            logging.warning("couldn't get internet_check")
            return 0
        logger.info("internet_check is: " + str(internet_check.val()))
        return int(internet_check.val())


    def getBoxLatestVersion(self) -> str:
        latestVersion = self.database.child("box").child("latest_version").get()
        if latestVersion.val() is None:
            logger.warning("couldn't get latest_version")
            return "unknown"
        return str(latestVersion.val())
