from boxsettings import BoxSettings
from stepper import Stepper
from boxstate import BoxState
from boxcircle import BoxCircle
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
import json
from datetimefunctions import DateTimeFunctions
import requests


folderPath = '/home/pi/'
os.makedirs(folderPath + "logs/", exist_ok=True)

logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                    datefmt='%Y-%m-%d:%H:%M:%S',
                    level=logging.INFO
                    )

requests_logger = logging.getLogger('urllib3')
requests_logger.setLevel(logging.ERROR)

logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setLevel(logging.INFO)
file_handler = logging.FileHandler(folderPath + "logs/podq.log")
file_handler.setLevel(logging.INFO)

logger.addHandler(handler)
logger.addHandler(file_handler)

logger.info("Starting podq with rotarymeds.py")

boxState = BoxState()
boxSettings = BoxSettings()

pinConfigFilePath = '/home/pi/pinlayout.json'
with open(pinConfigFilePath, 'r') as f:
    pinConfigToBeLoaded = json.load(f)

ir_pin = pinConfigToBeLoaded['ir_pin']
button_led_pin = pinConfigToBeLoaded['button_led_pin']
button_pushed_pin = pinConfigToBeLoaded['button_pushed_pin']

stepper_inner_in1 = pinConfigToBeLoaded['stepper_inner_in1']
stepper_inner_in2 = pinConfigToBeLoaded['stepper_inner_in2']
stepper_inner_in3 = pinConfigToBeLoaded['stepper_inner_in3']
stepper_inner_in4 = pinConfigToBeLoaded['stepper_inner_in4']
chanListInner = [stepper_inner_in1, stepper_inner_in2,
                 stepper_inner_in3, stepper_inner_in4]

stepper_outer_in1 = pinConfigToBeLoaded['stepper_outer_in1']
stepper_outer_in2 = pinConfigToBeLoaded['stepper_outer_in2']
stepper_outer_in3 = pinConfigToBeLoaded['stepper_outer_in3']
stepper_outer_in4 = pinConfigToBeLoaded['stepper_outer_in4']
chanListOuter = [stepper_outer_in1, stepper_outer_in2,
                 stepper_outer_in3, stepper_outer_in4]

led_pin = pinConfigToBeLoaded['led_pin']
boxState.version = "1.0.24"
logger.info("podq version is " + boxState.version)


def getserial():
    cpuserial = "123456789123456789"
    try:
        f = open('/proc/cpuinfo', 'r')
        for line in f:
            if line[0:6] == 'Serial':
                cpuserial = line[10:26].replace('0', '')
        f.close()
    except:
        cpuserial = "ERROR000000000"
        logging.error("cpuserial was not found")
    return cpuserial


boxState.cpuId = getserial()
logger.info("CPU serial is [" + str(boxState.cpuId) + "]")

innerCircle = BoxCircle("innerCircle", boxState.cpuId)
outerCircle = BoxCircle("outerCircle", boxState.cpuId)

googleHostForInternetCheck = "8.8.8.8"


def haveInternet():
    try:
        output = subprocess.check_output(
            "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)
    except Exception:
        return False
    return True


logger.info("checking internet connectivity")
while(not haveInternet()):
    logger.info("internet is not available, sleeping 1 second")
    time.sleep(1)
logger.info("have internet connectivity")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((googleHostForInternetCheck, 0))
boxState.ipAddress = s.getsockname()[0]
boxState.hostname = socket.gethostname()

logger.info("Creating FirebaseConnection")
firebaseConnection = FirebaseConnection(str(boxState.cpuId))
logger.info("Done creating FirebaseConnection")

defaultstepperInner = {"minMove": 2000, "maxMove": 2500,
                       "afterTrigger": 1360, "chanList": chanListInner}
defaultstepperOuter = {"minMove": 2100, "maxMove": 2900,
                       "afterTrigger": 1460, "chanList": chanListOuter}
defaultLatestMove = {
    "totalSteps": 0,
    "irTriggered": False,
    "stepsAfterTrigger": 0,
    "timestamp": "1900-01-01 00:00:00",
    "timestampEpoch": 0,
}


def getFirebaseValuesAndSetDefaultsIfNeeded():
    getTimezone()
    getSchedules()
    innerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue(
        "nrPockets", 7, "settings", innerCircle.name,"circles")
    getStepper(innerCircle, defaultstepperInner)
    outerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue(
        "nrPockets", 7, "settings", outerCircle.name,"circles")
    getStepper(outerCircle, defaultstepperOuter)
    innerCircle.state.latestMove = firebaseConnection.getFirebaseValue(
        "latestMove", defaultLatestMove, "state", innerCircle.name,"circles")
    innerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue(
        "pocketsFull", 0, "state", innerCircle.name,"circles")
    outerCircle.state.latestMove = firebaseConnection.getFirebaseValue(
        "latestMove", defaultLatestMove, "state", outerCircle.name,"circles")
    outerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue(
        "pocketsFull", 0, "state", outerCircle.name,"circles")


def getTimezone():
    boxSettings.timezone = firebaseConnection.getFirebaseValue(
        "timezone", "Europe/London", "settings")



def getStepper(circle: BoxCircle, defaultstepper):
    firebaseStepSettings = firebaseConnection.getFirebaseValue(
        "stepper",  defaultstepper, "settings", circle.name, "circles")
    circle.settings.stepper.afterTrigger = firebaseStepSettings["afterTrigger"]
    circle.settings.stepper.maxMove = firebaseStepSettings["maxMove"]
    circle.settings.stepper.minMove = firebaseStepSettings["minMove"]
    circle.settings.stepper.chanList = firebaseStepSettings["chanList"]


def getSchedules():
    defaultSchedule = [{"day": "everyday", "hour": 7, "minute": 0}]
    innerCircle.settings.schedules = firebaseConnection.getFirebaseValue(
        'schedules', defaultSchedule, "settings", innerCircle.name,"circles")
    outerCircle.settings.schedules = firebaseConnection.getFirebaseValue(
        'schedules', defaultSchedule, "settings", outerCircle.name,"circles")


getFirebaseValuesAndSetDefaultsIfNeeded()

firebaseConnection.setFirebaseValue("setButtonLed", False, "commands")
firebaseConnection.setFirebaseValue(
    "moveNow", False, "commands", innerCircle.name,"circles")
firebaseConnection.setFirebaseValue(
    "setPocketsFull", False, "commands", innerCircle.name,"circles")
firebaseConnection.setFirebaseValue(
    "moveNow", False, "commands", outerCircle.name,"circles")
firebaseConnection.setFirebaseValue(
    "setPocketsFull", False, "commands", outerCircle.name,"circles")

exitapp = False
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_led_pin, GPIO.OUT)
GPIO.setup(button_pushed_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin, GPIO.LOW)
GPIO.setup(ir_pin, GPIO.IN)

arr1 = [1, 1, 0, 0]
arr2 = [0, 1, 0, 0]
arrOff = [0, 0, 0, 0]

for pin in innerCircle.settings.stepper.chanList:
    GPIO.setup(pin, GPIO.OUT)
for pin in outerCircle.settings.stepper.chanList:
    GPIO.setup(pin, GPIO.OUT)

moveIsBeingDone = False


def move_stepper(circle: BoxCircle):
    global moveIsBeingDone
    while (moveIsBeingDone):
        logger.info(circle.name + " : waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move(circle)
    circle.state.pocketsFull = max(circle.state.pocketsFull - 1, 0)
    firebaseConnection.setFirebaseValue(
        "pocketsFull", circle.state.pocketsFull, "state", circle.name, "circles")
    moveIsBeingDone = False


def holdBothMotors():
    global arr1
    arrOUT = arr1[1:]+arr1[:1]
    GPIO.output(innerCircle.settings.stepper.chanList, arrOUT)
    GPIO.output(outerCircle.settings.stepper.chanList, arrOUT)


def releaseBothMotors():
    global arrOff
    GPIO.output(innerCircle.settings.stepper.chanList, arrOff)
    GPIO.output(outerCircle.settings.stepper.chanList, arrOff)


irTriggered = False


def move(circle: BoxCircle):
    logger.info("move called for " + str(circle))
    global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
    stepsDone = 0
    holdBothMotors()
    stepsDoneWhenIRtrigger = 0
    irTriggered = False

    def oneStep(stepsDone):
        global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
        # arrOUT = arr1[1:]+arr1[:1] for counterclockwise
        arrOUT = arr1[3:]+arr1[:3]
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(circle.settings.stepper.chanList, arrOUT)
        time.sleep(0.0012)
        if irTriggered and stepsDoneWhenIRtrigger == 0:
            stepsDoneWhenIRtrigger = stepsDone
        return stepsDone + 1

    while stepsDone < circle.settings.stepper.minMove:
        stepsDone = oneStep(stepsDone)

    while stepsDone < stepsDoneWhenIRtrigger + circle.settings.stepper.afterTrigger and stepsDone < circle.settings.stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    while irTriggered == False and stepsDone < circle.settings.stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    latestMove = {
        "totalSteps": stepsDone,
        "irTriggered": irTriggered,
        "stepsAfterTrigger": stepsDone - stepsDoneWhenIRtrigger,
        "timestamp": DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone).strftime(DateTimeFunctions.fmt),
        "timestampEpoch": time.time(),
    }
    logger.info("move complete    : " + circle.name + str(latestMove))
    circle.state.latestMove = latestMove
    firebaseConnection.setFirebaseValue(
        "latestMove", latestMove, "state", circle.name, "circles")
    GPIO.output(circle.settings.stepper.chanList, arrOff)
    setButtonLedOn(True)
    releaseBothMotors()


boxState.buttonLedOn = True


def setButtonLedOn(setToOn):
    if(setToOn):
        logger.info("setButtonLedOn    : turning ON the buttonLed")
        boxState.buttonLedOn = True
        GPIO.output(button_led_pin, GPIO.HIGH)
        GPIO.output(led_pin, GPIO.HIGH)
        firebaseConnection.setFirebaseValue("buttonLedOn", True, "state")
    else:
        logger.info("setButtonLedOn    : turning OFF the buttonLed")
        boxState.buttonLedOn = False
        GPIO.output(button_led_pin, GPIO.LOW)
        GPIO.output(led_pin, GPIO.LOW)
        firebaseConnection.setFirebaseValue("buttonLedOn", False, "state")


def getNextMove(schedules):
    nextMove = 0
    for schedule in schedules:
        candiate = DateTimeFunctions.getDateTimeFromScheduleWithTimezone(
            schedule['day'], schedule['hour'], schedule['minute'], boxSettings.timezone)
        if(candiate is None):
            logging.warning(
                "this is odd, candidate was None [" + str(schedule) + "]")
        else:
            if(nextMove == 0):
                nextMove = candiate
            elif(nextMove > candiate):
                nextMove = candiate
    return nextMove


def checkCommandSetButtonLed():
    newVal = firebaseConnection.getFirebaseValue(
        "setButtonLed", False, "commands")
    if(bool(newVal) is False):
        return
    logger.info(
        "firebase: setButtonLed has new value: " + str(newVal))
    if(newVal[:2] == "on"):
        setButtonLedOn(True)
    if(newVal[:3] == "off"):
        setButtonLedOn(False)
    firebaseConnection.setFirebaseValue("setButtonLed", False,  "commands")


def checkCommandMoveNow(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue(
        "moveNow", False, "commands", circle.name, "circles")
    if(bool(newVal)):
        logger.info("moveNow true for " + str(circle))
        firebaseConnection.setFirebaseValue(
            "moveNow", False, "commands", circle.name, "circles")
        move_stepper(circle)


def checkCommandsPockets(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue(
        "setPocketsFull", False, "commands", circle.name, "circles")
    if(newVal != False):
        logger.info(
            circle.name + " setPocketsFull called to be updated to " + str(int(newVal)))
        firebaseConnection.setFirebaseValue(
            "setPocketsFull", False, "commands", circle.name, "circles")
        firebaseConnection.setFirebaseValue(
            "pocketsFull", int(newVal), "state", circle.name, "circles")
        circle.state.pocketsFull = int(newVal)


def checkCommandsNodes():
    logger.info("checkCommandsNodes called")
    checkCommandSetButtonLed()
    checkCommandMoveNow(innerCircle)
    checkCommandMoveNow(outerCircle)
    checkCommandsPockets(innerCircle)
    checkCommandsPockets(outerCircle)


def stream_handler(message):
    try:
        path = "/settings/timezone"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "timezone", None, "settings")
            boxSettings.timezone = newVal
            firebaseConnection.setPing(boxSettings)
            getAndUpdateNextMoveFirebase(innerCircle)
            getAndUpdateNextMoveFirebase(outerCircle)
        path = "/circles/innerCircle/settings/schedules"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue(
                "schedules", None, "settings", innerCircle.name,"circles")
            getSchedules()
            getAndUpdateNextMoveFirebase(innerCircle)
        path = "/circles/outerCircle/settings/schedules"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue(
                "schedules", None, "settings", outerCircle.name,"circles")
            getSchedules()
            getAndUpdateNextMoveFirebase(outerCircle)
        path = "/circles/innerCircle/settings/stepper"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue(
                "stepper", None, "settings", innerCircle.name,"circles")
            getStepper(innerCircle, defaultstepperInner)
        path = "/circles/outerCircle/settings/stepper"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue(
                "stepper", None, "settings", outerCircle.name,"circles")
            getStepper(outerCircle, defaultstepperOuter)
        path = "/commands/setButtonLed"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "setButtonLed", None, "commands")
            checkCommandSetButtonLed()
        path = "/circles/innerCircle/commands/moveNow"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "moveNow", None, "commands", innerCircle.name,"circles")
            checkCommandMoveNow(innerCircle)
        path = "/circles/outerCircle/commands/moveNow"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "moveNow", None, "commands", outerCircle.name,"circles")
            checkCommandMoveNow(outerCircle)
        path = "/circles/innerCircle/commands/setPocketsFull"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "setPocketsFull", None, "commands", innerCircle.name,"circles")
            checkCommandsPockets(innerCircle)
        path = "/circles/outerCircle/commands/setPocketsFull"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue(
                "setPocketsFull", None, "commands", outerCircle.name,"circles")
            checkCommandsPockets(outerCircle)
    except Exception as err:
        logging.error("exception in stream_handler " + str(err) + " trace: " + traceback.format_exc())


def internetCheck(callingMethodName: str):
    global settingUpFirebaseStream
    internetWasLost = False
    skipFirebaseStreamSetup = False
    while(not haveInternet()):
        internetWasLost = True
        logger.info("internet is not available for [" + callingMethodName + "], sleeping")
        time.sleep(1)
    
    if(settingUpFirebaseStream):
        logger.info("other method is already doing setupStreamToFirebase so [" + callingMethodName + "], will return without calling it. Sleeping for now")
        skipFirebaseStreamSetup = True
        time.sleep(1)

    if(skipFirebaseStreamSetup):
        return

    if(internetWasLost):
        logger.info(
            "internet is back for [" + callingMethodName + "], resetting the stream to firebase")
        setupStreamToFirebase()

def thread_time(name):
    lastTimeStampUpdate = 0
    while not exitapp:
        try:
            time.sleep(5)
            internetCheck("thread_time")
            timestampNow = time.time()
            if(timestampNow - lastTimeStampUpdate > pingSeconds and timestampNow - lastTimeStampUpdate > 60):
                firebaseConnection.setPing(boxSettings)
                lastTimeStampUpdate = timestampNow
        except requests.exceptions.HTTPError as e:
           logging.error("HTTPError: [" + str(e).replace('\n', ' ').replace('\r', '') +"]")
        
        except Exception as err:
            logging.error("exception " + str(err) + " trace :" + traceback.format_exc())
    logger.info("thread_time    : exiting")

def getAndUpdateNextMoveFirebase(circle: BoxCircle):
    nextMove = getNextMove(circle.settings.schedules)
    nextMoveInEpoch = nextMove.timestamp()
    if(str(nextMove) != circle.state.nextMove):
        firebaseConnection.setFirebaseValue(
            "nextMove", str(nextMove).strip(), "state", circle.name, "circles")
    if(str(nextMoveInEpoch) != str(circle.state.nextMoveInEpoch)):
        firebaseConnection.setFirebaseValue(
            "nextMoveInEpoch", float(nextMoveInEpoch), "state", circle.name, "circles")
        circle.state.nextMoveInEpoch = nextMoveInEpoch
    return nextMove

def thread_move(circle: BoxCircle):
    lastMove = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone) - datetime.timedelta(days=-1)
    
    while not exitapp:
        try:
            internetCheck("thread_move_" + circle.name)
            
            nextMove = getAndUpdateNextMoveFirebase(circle)

            if(nextMove != 0):
                now = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
                secondsBetween = abs((now-nextMove).total_seconds())
                if(abs((now-lastMove).total_seconds()) < 60):
                    logger.info("thread_move" + circle.name +
                                 "    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logger.info("thread_move" + circle.name +
                                     "    :  it's time to move!")
                        lastMove = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
                        move_stepper(circle)
        except requests.exceptions.HTTPError as e:
            logging.error("HTTPError: [" + str(e).replace('\n', ' ').replace('\r', '') +"]")
            
                    
        except Exception as err:
            logging.error("exception: [" + str(err) + "] the trace: [" + traceback.format_exc() + "]")
        time.sleep(5)
    logger.info("thread_move" + circle.name + "    :   exiting")


def thread_move_inner(name):
    thread_move(innerCircle)


def thread_move_outer(name):
    thread_move(outerCircle)


def thread_button(name):
    timeButtonPressMostRecent = 0
    timeButtonNotPressed = 0
    while not exitapp:
        try:
            if GPIO.input(button_pushed_pin) == GPIO.HIGH:
                timestampNow = time.time()

                if(timeButtonNotPressed > timeButtonPressMostRecent):
                    logger.info(
                        "thread_button    : button_pushed_pin button was pushed!")
                    if(boxState.buttonLedOn):
                        setButtonLedOn(False)
                    else:
                        setButtonLedOn(True)
                    timeButtonPressMostRecent = timestampNow
            else:
                timeButtonNotPressed = time.time()
            time.sleep(0.1)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())

    logger.info("thread_button    : exiting")


def thread_ir_sensor(name):
    global irTriggered
    lastBlack = 0
    lastWhite = 0
    while not exitapp:
        try:
            if(irTriggered == False):
                if GPIO.input(ir_pin) == GPIO.LOW:
                    lastWhite = time.time()
                else:
                    lastBlack = time.time()

                if(lastWhite > lastBlack):  # just turned white
                    irTriggered = True
                    logger.info("thread_ir_sensor    : irTriggered")
            time.sleep(0.05)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())

    logger.info("thread_ir_sensor    : exiting")


my_stream = ""

settingUpFirebaseStream = False
def setupStreamToFirebase():
    global settingUpFirebaseStream
    settingUpFirebaseStream = True
    global my_stream
    try:
        if(my_stream != ""):
            my_stream.close()
    except Exception as err:
        logger.info("tried to close the stream but failed " + str(err) + " trace: " + traceback.format_exc())

    logger.info("setting up the stream to firebase")
    my_stream = firebaseConnection.database.child("box").child(
        "boxes").child(boxState.cpuId).stream(stream_handler)
    logger.info("done setting up the stream to firebase")
    settingUpFirebaseStream = False
    checkCommandsNodes()
    


if __name__ == '__main__':
    try:
        timestampNow = time.time()
        timeGreenButtonPushed = timestampNow + 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        firebaseConnection.setFirebaseValue("cpuId", boxState.cpuId, "state")
        firebaseConnection.setFirebaseValue(
            "cpuId", boxState.cpuId, "innerCircle","circles")
        firebaseConnection.setFirebaseValue(
            "name", innerCircle.name, innerCircle.name,"circles")
        firebaseConnection.setFirebaseValue(
            "cpuId", boxState.cpuId, "outerCircle","circles")
        firebaseConnection.setFirebaseValue(
            "name", outerCircle.name, outerCircle.name,"circles")
        firebaseConnection.setFirebaseValue(
            "ipAddress", boxState.ipAddress, "state")
        firebaseConnection.setFirebaseValue(
            "hostname", boxState.hostname, "state")
        firebaseConnection.setFirebaseValue(
            "version", boxState.version, "state")

        latestVersionAvailable = firebaseConnection.getBoxLatestVersion()
        pingSeconds = int(firebaseConnection.getPingSeconds())

        if(boxState.version != latestVersionAvailable):
            if(latestVersionAvailable == "unknown"):
                logging.error("unable to get latest_version from firebase")
            else:
                logging.warning(
                    "our version [" + boxState.version + "] latest_version [" + latestVersionAvailable + "]")
        else:
            logger.info(
                "OK our version [" + boxState.version + "] latest_version [" + latestVersionAvailable + "]")

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
        logger.info("Keyboard interrupt")
    except Exception as err:
        logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    finally:
        logger.info("Main    : cleaning up the GPIO and exiting")
        setButtonLedOn(False)
        exitapp = True
        GPIO.cleanup()
        logging
        my_stream.close()
        # give the threads time to shut down before removing GPIO
        time.sleep(1)
        logger.info("Main    : Shutdown complete")
    logger.info("Main    : Goodbye!")
