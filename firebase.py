import pyrebase
import json

class FirebaseConnection:
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


    def setFirebaseValue(self, settingname, newValue):
        logging.info("getting [" + str(settingname) +
                    "] from firebase as part of setFirebaseValue, setting it to [" + str(newValue) + "]")
        currentValue = self.database.child("box").child(
            "boxes").child(boxState.cpuId).child(settingname).get()
        if(currentValue.val() != newValue):
            self.database.child("box").child("boxes").child(
                boxState.cpuId).child(settingname).set(newValue)
            if(settingname != "timestamp"):
                logging.info("updated [" + settingname + "] from [" +
                            str(currentValue.val()) + "] to[" + str(newValue) + "]")


    def getFirebaseValue(self, settingname, defaultValue):
        settingValue = self.database.child("box").child(
            "boxes").child(boxState.cpuId).child(settingname).get()
        if settingValue.val() is None:
            setFirebaseValue(settingname, defaultValue)
        returnVal = self.database.child("box").child("boxes").child(
            boxState.cpuId).child(settingname).get().val()
        logging.info("getting firebase value [" + settingname + "]")
        return returnVal


    def getLatestBoxVersionAvailable(self):
        latestVersion = self.database.child("box").child("latest_version").get()
        if latestVersion.val() is None:
            logging.warning("couldn't get latest_version")
            return "unknown"

        logging.info("latest_version is: " + str(latestVersion.val()))
        return str(latestVersion.val())
