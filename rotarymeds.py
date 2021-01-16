import os
import logging
from typing import List
import RPi.GPIO as GPIO
import datetime
from datetime import timedelta  
import time
import threading
import socket  # used for hostname
import traceback
import subprocess

from firebase import FirebaseConnection
from box import Box
from datetimefunctions import DateTimeFunctions

folderPath = '/home/pi/shared/'
os.makedirs(folderPath + "logs/", exist_ok=True)
logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO,
                    handlers=[
                        logging.FileHandler(
                            folderPath + "logs/rotarymeds.log"),
                        logging.StreamHandler()
                    ])
logging.info("Starting rotarymeds.py")

box = Box()


box.boxState.version = "1.0.20"
logging.info("version is " + box.boxState.version)

googleHostForInternetCheck = "8.8.8.8"


def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
        logging.error("cpuserial was not found")

    return cpuserial


box.boxState.cpuId = getserial()

logging.info("CPU serial is [" + str(box.boxState.cpuId) + "]")


logging.info("checking internet connectivity")

def haveInternet():
    try:
        output = subprocess.check_output(
            "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)

    except Exception:
        return False

    return True

while(not haveInternet()):
    logging.info("internet is not available, sleeping 1 second")
    time.sleep(1)

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((googleHostForInternetCheck, 0))
box.boxState.ipAddress = s.getsockname()[0]
box.boxState.hostname = socket.gethostname()

logging.info("have internet connectivity")

logging.info("Creating FirebaseConnection")
firebaseConnection = FirebaseConnection(str(box.boxState.cpuId))
logging.info("Done creating FirebaseConnection")

def getFirebaseValuesAndSetDefaultsIfNeeded():

    defaultSchedule =[{"day": "everyday", "hour":7, "minute":0}]

    box.boxSettings.scheduleInner = firebaseConnection.getFirebaseValue('scheduleInner', defaultSchedule, "settings")
    box.boxSettings.scheduleOuter = firebaseConnection.getFirebaseValue('scheduleOuter', defaultSchedule, "settings")

    defaultStepSettingsInner = {"name": "inner", "minMove": 2000, "maxMove": 2500, "afterTrigger": 1360, "chanList": [17, 27, 22, 23]} 
    defaultStepSettingsOuter = {"name": "outer", "minMove": 2100, "maxMove": 2600, "afterTrigger": 1640, "chanList": [24, 13, 26, 12]} 
    
    
    innerStepSettnigs = firebaseConnection.getFirebaseValue("stepSettingsInner",  defaultStepSettingsInner, "settings")
    outerStepSettnigs = firebaseConnection.getFirebaseValue("stepSettingsOuter",  defaultStepSettingsOuter, "settings")
    
    box.boxSettings.innerStepper.afterTrigger = innerStepSettnigs["afterTrigger"]
    box.boxSettings.innerStepper.maxMove = innerStepSettnigs["maxMove"]
    box.boxSettings.innerStepper.minMove = innerStepSettnigs["minMove"]
    box.boxSettings.innerStepper.chanList = innerStepSettnigs["chanList"]  # GPIO ports to use
    box.boxSettings.innerStepper.name = innerStepSettnigs["name"]
    
    box.boxSettings.outerStepper.afterTrigger = outerStepSettnigs["afterTrigger"]
    box.boxSettings.outerStepper.maxMove = outerStepSettnigs["maxMove"]
    box.boxSettings.outerStepper.minMove = outerStepSettnigs["minMove"]
    box.boxSettings.outerStepper.chanList = outerStepSettnigs["chanList"]  # GPIO ports to use
    box.boxSettings.outerStepper.name = outerStepSettnigs["name"]
    box.boxSettings.innerPockets = firebaseConnection.getFirebaseValue("innerPockets", 7, "settings")
    box.boxSettings.outerPockets = firebaseConnection.getFirebaseValue("outerPockets", 7, "settings")

    defaultLatestMove = {
        "totalSteps": 0,
        "irTriggered": 0,
        "stepsAfterTrigger": 0,
        "timestamp": "1900-01-01 00:00:00",
    }
    box.boxState.latestMoveInner = firebaseConnection.getFirebaseValue("latestMoveInner", defaultLatestMove, "state")
    box.boxState.latestMoveOuter = firebaseConnection.getFirebaseValue("latestMoveOuter", defaultLatestMove, "state")
    box.boxState.pocketsFullInner = firebaseConnection.getFirebaseValue("pocketsFullInner", 0, "state")
    box.boxState.pocketsFullOuter = firebaseConnection.getFirebaseValue("pocketsFullOuter", 0, "state")



getFirebaseValuesAndSetDefaultsIfNeeded()


firebaseConnection.setFirebaseValue("moveNowInner", False, "commands")
firebaseConnection.setFirebaseValue("moveNowOuter", False, "commands")
firebaseConnection.setFirebaseValue("setButtonLed", False, "commands")
firebaseConnection.setFirebaseValue("setPocketsFullInner", False, "commands")
firebaseConnection.setFirebaseValue("setPocketsFullOuter", False, "commands")

GPIO.setmode(GPIO.BCM)

exitapp = False

buttonLedPin = 6
GPIO.setup(buttonLedPin, GPIO.OUT)

buttonPin = 5
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

whiteLedPin = 16
GPIO.setup(whiteLedPin, GPIO.OUT)
GPIO.output(whiteLedPin, GPIO.LOW)

irSensorPin = 4
GPIO.setup(irSensorPin, GPIO.IN)


# initialize array for sequence shift
arr1 = [1, 1, 0, 0]
arr2 = [0, 1, 0, 0]
arrOff = [0, 0, 0, 0]



for pin in box.boxSettings.innerStepper.chanList:
    GPIO.setup(pin, GPIO.OUT)
for pin in box.boxSettings.outerStepper.chanList:
    GPIO.setup(pin, GPIO.OUT)


moveIsBeingDone = False


def move_stepper_inner():
    global moveIsBeingDone
    while (moveIsBeingDone):
        logging.info("inner: waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move(box.boxSettings.innerStepper)
    box.boxState.pocketsFullInner = max(box.boxState.pocketsFullInner -1, 0)
    firebaseConnection.setFirebaseValue("pocketsFullInner", box.boxState.pocketsFullInner, "state")
    moveIsBeingDone = False


def move_stepper_outer():
    global moveIsBeingDone
    while (moveIsBeingDone):
        logging.info("outer: waiting for other move to be done",
                     moveIsBeingDone)
        time.sleep(1)
    moveIsBeingDone = True
    move(box.boxSettings.outerStepper)
    box.boxState.pocketsFullOuter = max(box.boxState.pocketsFullOuter -1, 0)
    firebaseConnection.setFirebaseValue("pocketsFullOuter", box.boxState.pocketsFullOuter, "state")
    moveIsBeingDone = False


def holdBothMotors():
    global arr1  # enables the edit of arr1 var inside a function
    arrOUT = arr1[1:]+arr1[:1]  # rotates array values of 1 digi
    GPIO.output(box.boxSettings.innerStepper.chanList, arrOUT)
    GPIO.output(box.boxSettings.outerStepper.chanList, arrOUT)


def releaseBothMotors():
    global arrOff
    GPIO.output(box.boxSettings.innerStepper.chanList, arrOff)
    GPIO.output(box.boxSettings.outerStepper.chanList, arrOff)


irTriggered = False

def move(stepper):
    global irTriggered
    global arr1  # enables the edit of arr1 var inside a function
    global arr2  # enables the edit of arr2 var inside a function

    stepsDone = 0

    holdBothMotors()

    global stepsDoneWhenIRtrigger
    stepsDoneWhenIRtrigger = 0
    irTriggered = False

    def oneStep(stepsDone):
        global arr1
        global arr2
        global irTriggered
        global stepsDoneWhenIRtrigger
        arrOUT = arr1[3:]+arr1[:3]  # rotates array values of 1 digi
        # arrOUT = arr1[1:]+arr1[:1] # rotates array values of 1 digit counterclockwise
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(stepper.chanList, arrOUT)
        time.sleep(0.002)
        if irTriggered and stepsDoneWhenIRtrigger == 0:
            stepsDoneWhenIRtrigger = stepsDone
        return stepsDone + 1

    while stepsDone < stepper.minMove:
        stepsDone = oneStep(stepsDone)

    while stepsDone < stepsDoneWhenIRtrigger + stepper.afterTrigger and stepsDone < stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    while irTriggered == False and stepsDone < stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    logMessage = stepper.name + " totalSteps [" + str(stepsDone) + "] irTriggered [" + str(irTriggered) + "] stepsAfterTrigger [" + str(stepsDone - stepsDoneWhenIRtrigger) + "]"
    logging.info("move    : " + logMessage)
    now = datetime.datetime.now()

    latestMove = {
        "totalSteps": stepsDone,
        "irTriggered": irTriggered,
        "stepsAfterTrigger": stepsDone - stepsDoneWhenIRtrigger,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
    }
    if(stepper.name == "inner"):
        box.boxState.latestMoveInner = latestMove
        firebaseConnection.setFirebaseValue("latestMoveInner", latestMove, "state")
    else:
        box.boxState.latestMoveOuter = latestMove
        firebaseConnection.setFirebaseValue("latestMoveOuter", latestMove, "state")

    
    GPIO.output(stepper.chanList, arrOff)

    setButtonLedOn(True)

    releaseBothMotors()
    logging.info(" ")


box.boxState.buttonLedOn = True


def setButtonLedOn(setToOn):
    if(setToOn):
        logging.info("setButtonLedOn    : turning ON the buttonLed")
        box.boxState.buttonLedOn = True
        GPIO.output(buttonLedPin, GPIO.HIGH)
        GPIO.output(whiteLedPin, GPIO.HIGH)
        firebaseConnection.setFirebaseValue("buttonLedOn", True, "state")

    else:
        logging.info("setButtonLedOn    : turning OFF the buttonLed")
        box.boxState.buttonLedOn = False
        GPIO.output(buttonLedPin, GPIO.LOW)
        GPIO.output(whiteLedPin, GPIO.LOW)
        firebaseConnection.setFirebaseValue("buttonLedOn", False, "state")


def getNextMove(innerOrOuter):
    if(innerOrOuter == "inner"):
        schedule = box.boxSettings.scheduleInner
        currentCachedValue = box.boxState.nextMoveInner
    else:
        schedule = box.boxSettings.scheduleOuter
        currentCachedValue = box.boxState.nextMoveOuter

    nextMove = 0
    for scheduledMove in schedule:
        candiate = DateTimeFunctions.dateTimeFromSchedule(scheduledMove['day'], scheduledMove['hour'], scheduledMove['minute'])
        if(candiate is None):
            logging.warning("this is odd, candidate was None [" + str(scheduledMove) + "]")
        else:
            if(nextMove == 0):
                nextMove = candiate
            elif(nextMove > candiate):
                nextMove = candiate
                
    if(str(nextMove) != str(currentCachedValue)):
        firebaseConnection.setFirebaseValue(
            str("nextMove" + str(innerOrOuter.capitalize())), str(nextMove).strip(), "state")
        if(innerOrOuter == "inner"):
            box.boxState.nextMoveInner = nextMove
        else:
            box.boxState.nextMoveOuter = nextMove
    return nextMove


def checkCommandSetButtonLed():
    newVal = firebaseConnection.getFirebaseValue("setButtonLed", False, "commands")
    if(bool(newVal) is False):
        return
    logging.info(
        "firebase: setButtonLed has new value: " + str(newVal))
    if(newVal == "on"):
        setButtonLedOn(True)
    if(newVal == "off"):
        setButtonLedOn(False)
    firebaseConnection.setFirebaseValue("setButtonLed", False,  "commands")

def checkCommandMoveNowOuter():
    newVal = firebaseConnection.getFirebaseValue("moveNowOuter", False, "commands")
    if(bool(newVal)):
        logging.info(
            "we should move outer now, setting moveNowOuter to false before moving to avoid multiple triggers")
        firebaseConnection.setFirebaseValue("moveNowOuter", False, "commands")
        move_stepper_outer()

def checkCommandMoveNowInner():
    newVal = firebaseConnection.getFirebaseValue("moveNowInner", False, "commands")
    if(bool(newVal)):
        logging.info(
            "we should move outer now, setting moveNowInner to false before moving to avoid multiple triggers")
        firebaseConnection.setFirebaseValue("moveNowInner", False, "commands")
        move_stepper_inner()

def checkCommandsPockets(innerOrOuter):
    settingName = "setPocketsFull" + innerOrOuter

    newVal = firebaseConnection.getFirebaseValue(settingName, False, "commands")
    if(newVal != False):
        logging.info(
            settingName + " called to be updated to " + str(int(newVal)))
        firebaseConnection.setFirebaseValue(settingName, False, "commands")
        firebaseConnection.setFirebaseValue("pocketsFull" + innerOrOuter, int(newVal), "state")
        box.boxState.pocketsFullInner = int(newVal)
        logging.info(
            settingName + " updated to " + str(int(newVal)))

def checkCommandsNodes():
    logging.info("checkCommandsNodes called")
    checkCommandSetButtonLed()
    checkCommandMoveNowOuter()
    checkCommandMoveNowInner()
    checkCommandsPockets("Inner")
    checkCommandsPockets("Outer")
    

# TODO there could be issues where these are set while the internet is down (as checked in thread_time), would miss an update if it is
def stream_handler(message):
    try:
        if message["path"].startswith("/settings/scheduleInner"):
            newVal = firebaseConnection.getFirebaseValue("scheduleInner",None,"settings")
            logging.info("firebase: scheduleInner has new value: " + str(newVal))
            getFirebaseValuesAndSetDefaultsIfNeeded()
        if message["path"].startswith("/settings/scheduleOuter"):
            newVal = firebaseConnection.getFirebaseValue("scheduleOuter",None,"settings")
            logging.info("firebase: scheduleOuter has new value: " + str(newVal))
            getFirebaseValuesAndSetDefaultsIfNeeded()
        if message["path"] == "/commands/setButtonLed":
            checkCommandSetButtonLed()
        if message["path"] == "/commands/moveNowOuter":
           checkCommandMoveNowOuter()
        if message["path"] == "/commands/moveNowInner":
            checkCommandMoveNowInner()
        if message["path"] == "/commands/setPocketsFullInner":
            checkCommandsPockets("Inner")
        if message["path"] == "/commands/setPocketsFullOuter":
            checkCommandsPockets("Outer")
    except Exception:
        logging.error("exception in stream_handler " + traceback.format_exc())


def thread_time(name):
    lastTimeStampUpdate = 0

    while not exitapp:
        try:
            time.sleep(5)
            now = datetime.datetime.now()
            timestampNow = time.time()

            internetWasLost = False
            while(not haveInternet()):
                internetWasLost = True
                logging.info("internet is not available, sleeping 1 second")
                time.sleep(1)

            if(internetWasLost):
                logging.info(
                    "internet is back, resetting the stream to firebase")
                setupStreamToFirebase()

            if(timestampNow - lastTimeStampUpdate > 60):
                firebaseConnection.setFirebaseValue(
                    "timestamp", now.strftime('%Y-%m-%d %H:%M:%S'))
                lastTimeStampUpdate = timestampNow

        except Exception as err:
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_time    : exiting")


def thread_move_inner(name):
    lastMove = datetime.datetime.now() + datetime.timedelta(days=-1)

    while not exitapp:
        try:
            nextMove = getNextMove("inner")
            if(nextMove != 0):
                now = datetime.datetime.now()

                secondsBetween = abs((now-nextMove).total_seconds())

                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info(
                        "thread_move_inner    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logging.info(
                            "thread_move_inner    :  it's time to move!")
                        lastMove = now
                        move_stepper_inner()
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

        time.sleep(5)

    logging.info("thread_move_inner    :   exiting")


def thread_move_outer(name):
    lastMove = datetime.datetime.now() + datetime.timedelta(days=-1)

    while not exitapp:
        try:
            nextMove = getNextMove("outer")
            if(nextMove != 0):
                now = datetime.datetime.now()

                secondsBetween = abs((now-nextMove).total_seconds())

                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info(
                        "thread_move_outer    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logging.info(
                            "thread_move_outer    :  it's time to move!")
                        lastMove = now
                        move_stepper_outer()
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

        time.sleep(5)

    logging.info("thread_move_outer    :   exiting")


def thread_button(name):

    timeButtonPressMostRecent = 0
    timeButtonNotPressed = 0

    while not exitapp:
        try:
            if GPIO.input(buttonPin) == GPIO.HIGH:
                timestampNow = time.time()

                if(timeButtonNotPressed > timeButtonPressMostRecent):
                    logging.info(
                        "thread_button    : buttonPin button was pushed!")

                    if(box.boxState.buttonLedOn):
                        setButtonLedOn(False)
                    else:
                        setButtonLedOn(True)
                    timeButtonPressMostRecent = timestampNow
            else:
                timeButtonNotPressed = time.time()
            time.sleep(0.1)
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_button    : exiting")


def thread_ir_sensor(name):
    global irTriggered

    lastBlack = 0
    lastWhite = 0

    while not exitapp:
        try:
            if(irTriggered == False):
                if GPIO.input(irSensorPin) == GPIO.LOW:
                    lastWhite = time.time()
                else:
                    lastBlack = time.time()

                if(lastWhite > lastBlack):  # just turned white
                    irTriggered = True
                    logging.info("thread_ir_sensor    : irTriggered")
            time.sleep(0.05)
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_ir_sensor    : exiting")


my_stream = ""


def setupStreamToFirebase():
    global my_stream
    try:
        if(my_stream != ""):
            my_stream.close()
    except Exception as err:
        logging.info("tried to close the stream but failed")

    logging.info("setting up the stream to firebase")
    my_stream = firebaseConnection.database.child("box").child(
        "boxes").child(box.boxState.cpuId).stream(stream_handler)
    logging.info("done setting up the stream to firebase")
    checkCommandsNodes()




if __name__ == '__main__':

    try:
        timestampNow = time.time()
        timeGreenButtonPushed = timestampNow + 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        firebaseConnection.setFirebaseValue("cpuId", box.boxState.cpuId, "state")
        firebaseConnection.setFirebaseValue("ipAddress", box.boxState.ipAddress, "state")
        firebaseConnection.setFirebaseValue("hostname", box.boxState.hostname, "state")
        firebaseConnection.setFirebaseValue("version", box.boxState.version, "state")


        latestVersionAvailable = firebaseConnection.getBoxLatestVersion()
        if(box.boxState.version != latestVersionAvailable):
            if(latestVersionAvailable == "unknown"):
                logging.error("unable to get latest_version from firebase")
            else:
                logging.warning(
                    "our version [" + box.boxState.version + "] latest_version [" + latestVersionAvailable + "]")
        else:
            logging.info(
                "OK our version [" + box.boxState.version + "] latest_version [" + latestVersionAvailable + "]")

        buttonThread = threading.Thread(target=thread_button, args=(1,))
        buttonThread.start()

        irThread = threading.Thread(target=thread_ir_sensor, args=(1,))
        irThread.start()

        timeThread = threading.Thread(target=thread_time, args=(1,))
        timeThread.start()

        setupStreamToFirebase()

        moveThreadInner = threading.Thread(target=thread_move_inner, args=(1,))
        moveThreadInner.start()

        moveThreadOuter = threading.Thread(target=thread_move_outer, args=(1,))
        moveThreadOuter.start()

        releaseBothMotors()
        setButtonLedOn(True)

        while (True):
            time.sleep(10)

    except KeyboardInterrupt:  # If CTRL+C is pressed, exit cleanly:
        logging.info("Keyboard interrupt")

    except Exception:
        logging.error("exception " + traceback.format_exc())

    finally:
        logging.info("Main    : cleaning up the GPIO and exiting")
        setButtonLedOn(False)
        exitapp = True
        GPIO.cleanup()
        logging
        my_stream.close()
        # give the threads time to shut down before removing GPIO
        time.sleep(1)
        logging.info("Main    : Shutdown complete")

    logging.info("Main    : Goodbye!")
