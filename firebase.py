import pyrebase
import json
import logging

class FirebaseConnection:
    cpuid = 0
    
    def __init__(self, cpuid):
        self.cpuid = cpuid
        

    configFilePath = '/home/pi/shared/config.json'
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


    def setFirebaseValue(self, settingname, newValue, parent = None, grandparent = None):
        logging.info("getting [" + str(settingname) +
                    "] from firebase as part of setFirebaseValue, setting it to [" + str(newValue) + "]")
        
        if(parent is None):
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get()
        elif(grandparent is None):
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get()
        else:
            currentValue = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get()

        if(currentValue.val() != newValue):
            
            if(parent is None):
                self.database.child("box").child("boxes").child(self.cpuid).child(settingname).set(newValue)
            elif(grandparent is None):
                self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).set(newValue)
            else:
                self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).set(newValue)

            if(settingname != "timestamp"):
                logMessasge = settingname
                if(parent is not None):
                    logMessasge = parent + "/" + logMessasge
                    if(grandparent is not None):
                        logMessasge = grandparent + "/" + logMessasge
                logging.info("updated [" + logMessasge + "] from [" +
                            str(currentValue.val()) + "] to[" + str(newValue) + "]")


    def getFirebaseValue(self, settingname, defaultValue = None, parent = None, grandparent = None):
        if(parent is None):
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get()
        elif(grandparent is None):
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get()
        else:
            settingValue = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get()
        
        if settingValue.val() is None:
            if defaultValue is None:
                logging.warning("getFirebaseValue for [" + settingname + "] has no default value and no current value")
                return None
            self.setFirebaseValue(settingname, defaultValue, parent, grandparent)
        
        if(grandparent is not None):
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(grandparent).child(parent).child(settingname).get().val()
        elif(parent is not None):
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(parent).child(settingname).get().val()
        else:
            returnVal = self.database.child("box").child("boxes").child(self.cpuid).child(settingname).get().val()
        
        logging.info("getting firebase value [" + settingname + "]")
        return returnVal


    def getBoxLatestVersion(self):
        latestVersion = self.database.child("box").child("latest_version").get()
        if latestVersion.val() is None:
            logging.warning("couldn't get latest_version")
            return "unknown"

        logging.info("latest_version is: " + str(latestVersion.val()))
        return str(latestVersion.val())
