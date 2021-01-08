
import os
import logging
from typing import List
import RPi.GPIO as GPIO
import datetime
import time
import threading
import json
import socket  # used for hostname
import traceback
import subprocess

from firebase import FirebaseConnection
from box import Box

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


box.boxSettings.version = "1.0.19"
logging.info("version is " + box.boxSettings.version)

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

logging.info("have internet connectivity")

logging.info("Creating FirebaseConnection")
firebaseConnection = FirebaseConnection(str(box.boxState.cpuId))
logging.info("Done creating FirebaseConnection")

def getFirebaseValuesAndSetDefaultsIfNeeded():
    global scheduleInner
    global scheduleOuter


    defaultSchedule = {"inner": [{"day": ["everyday"], "hour":7, "minute":0}], "outer": [
        {"day": ["everyday"], "hour":7, "minute":0}]}

    schedule = firebaseConnection.getFirebaseValue('schedule', defaultSchedule)
    scheduleOuter = schedule["outer"]
    scheduleInner = schedule["inner"]

    defaultStepSettings = {"inner": {"minMove": 2000, "maxMove": 2500, "afterTrigger": 1360}, "outer": {
        "minMove": 2100, "maxMove": 2600, "afterTrigger": 1640}}
    stepSettings = firebaseConnection.getFirebaseValue('stepSettings', defaultStepSettings)

    box.boxSettings.innerStepper.afterTrigger = stepSettings["inner"]["afterTrigger"]
    box.boxSettings.innerStepper.maxMove = stepSettings["inner"]["maxMove"]
    box.boxSettings.innerStepper.minMove = stepSettings["inner"]["minMove"]

    box.boxSettings.outerStepper.afterTrigger = stepSettings["outer"]["afterTrigger"]
    box.boxSettings.outerStepper.maxMove = stepSettings["outer"]["maxMove"]
    box.boxSettings.outerStepper.minMove = stepSettings["outer"]["minMove"]

    box.boxSettings.innerSchedule = scheduleInner

    defaultLatestMove = {
        "totalStepsDone": 0,
        "stopMoving": 0,
        "stepsDoneAfterIRtrigger": 0,
        "timestamp": "1900-01-01 00:00:00",
    }
    box.boxState.latestMoveInner = firebaseConnection.getFirebaseValue("inner", defaultLatestMove, "latestMove")
    box.boxState.latestMoveOuter = firebaseConnection.getFirebaseValue("outer", defaultLatestMove, "latestMove")

    logging.info("trying the json")
    logging.info(box.boxSettings.toJSON)
    firebaseConnection.setFirebaseValue("settings", box.boxSettings.toJSON)
    logging.info("done with the json")
    



getFirebaseValuesAndSetDefaultsIfNeeded()


firebaseConnection.setFirebaseValue("moveNowInner", False)
firebaseConnection.setFirebaseValue("moveNowOuter", False)
firebaseConnection.setFirebaseValue("setButtonLed", False)

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

delay = .001  # delay between each sequence step
# initialize array for sequence shift
arr1 = [1, 1, 0, 0]
arr2 = [0, 1, 0, 0]
arrOff = [0, 0, 0, 0]

box.boxSettings.innerStepper.chanList = [17, 27, 22, 23]  # GPIO ports to use
box.boxSettings.outerStepper.chanList = [24, 13, 26, 12]  # GPIO ports to useter
box.boxSettings.innerStepper.name = "inner"
box.boxSettings.outerStepper.name = "outer"

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
    moveIsBeingDone = False


def move_stepper_outer():
    global moveIsBeingDone
    while (moveIsBeingDone):
        logging.info("outer: waiting for other move to be done",
                     moveIsBeingDone)
        time.sleep(1)
    moveIsBeingDone = True
    move(box.boxSettings.outerStepper)
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


stopMoving = False


def move(stepper):
    global stopMoving
    global arr1  # enables the edit of arr1 var inside a function
    global arr2  # enables the edit of arr2 var inside a function

    stepsDone = 0

    holdBothMotors()

    global stepsDoneWhenIRtrigger
    stepsDoneWhenIRtrigger = 0
    stopMoving = False

    def oneStep(stepsDone):
        global arr1
        global arr2
        global stopMoving
        global stepsDoneWhenIRtrigger
        arrOUT = arr1[3:]+arr1[:3]  # rotates array values of 1 digi
        # arrOUT = arr1[1:]+arr1[:1] # rotates array values of 1 digit counterclockwise
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(stepper.chanList, arrOUT)
        time.sleep(delay)
        if stopMoving and stepsDoneWhenIRtrigger == 0:
            stepsDoneWhenIRtrigger = stepsDone
        return stepsDone + 1

    while stepsDone < stepper.minMove:
        stepsDone = oneStep(stepsDone)

    while stepsDone < stepsDoneWhenIRtrigger + stepper.afterTrigger and stepsDone < stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    while stopMoving == False and stepsDone < stepper.maxMove:
        stepsDone = oneStep(stepsDone)

    logMessage = stepper.name + " totalStepsDone [" + str(stepsDone) + "] stopMoving [" + str(stopMoving) + "] stepsDoneWhenIRtrigger [" + str(
        stepsDoneWhenIRtrigger) + "] stepsDoneAfterIRtrigger [" + str(stepsDone - stepsDoneWhenIRtrigger) + "] minimumMove [" + str(stepper.minMove) + "] maximumMove [" + str(stepper.maxMove) + "]"
    logging.info("move    : " + logMessage)
    now = datetime.datetime.now()

    latestMove = {
        "totalStepsDone": stepsDone,
        "stopMoving": stopMoving,
        "stepsDoneAfterIRtrigger": stepsDone - stepsDoneWhenIRtrigger,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
    }
    if(stepper.name == "inner"):
        box.boxState.latestMoveInner = latestMove
    else:
        box.boxState.latestMoveOuter = latestMove

    firebaseConnection.setFirebaseValue(stepper.name, latestMove, "latestMove")
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
        firebaseConnection.setFirebaseValue("buttonLedOn", True)

    else:
        logging.info("setButtonLedOn    : turning OFF the buttonLed")
        box.boxState.buttonLedOn = False
        GPIO.output(buttonLedPin, GPIO.LOW)
        GPIO.output(whiteLedPin, GPIO.LOW)
        firebaseConnection.setFirebaseValue("buttonLedOn", False)


def getWeekday(datetime):
    if datetime.weekday() == 0:
        return "Monday"
    if datetime.weekday() == 1:
        return "Tuesday"
    if datetime.weekday() == 2:
        return "Wednesday"
    if datetime.weekday() == 3:
        return "Thursday"
    if datetime.weekday() == 4:
        return "Friday"
    if datetime.weekday() == 5:
        return "Saturday"
    if datetime.weekday() == 6:
        return "Sunday"

    return "unknownDay"


nextMoveInner = 0
nextMoveOuter = 0


def getNextMove(innerOrOuter):
    global nextMoveInner
    global nextMoveOuter

    if(innerOrOuter == "inner"):
        schedule = scheduleInner
        currentCachedValue = nextMoveInner
    else:
        schedule = scheduleOuter
        currentCachedValue = nextMoveOuter

    nextMove = 0
    todayWeekday = getWeekday(datetime.datetime.today())
    for scheduledMove in schedule:
        for dayInRecord in scheduledMove['day']:

            isTodayMoveDay = False

            if(dayInRecord == todayWeekday):
                isTodayMoveDay = True
            elif(dayInRecord == "everyday"):
                isTodayMoveDay = True

            if(isTodayMoveDay):
                moveDate = datetime.datetime.today()
                moveTime = datetime.time(
                    scheduledMove['hour'], scheduledMove['minute'], 0)
                possibleNextMove = datetime.datetime.combine(
                    moveDate, moveTime)
                if(possibleNextMove < datetime.datetime.now()):
                    break
                elif(nextMove == 0):
                    nextMove = possibleNextMove
                elif(possibleNextMove < nextMove):
                    nextMove = possibleNextMove

    if(str(nextMove) != str(currentCachedValue)):
        firebaseConnection.setFirebaseValue(
            str("nextMove" + str(innerOrOuter.capitalize())), str(nextMove).strip())
        if(innerOrOuter == "inner"):
            nextMoveInner = nextMove
        else:
            nextMoveOuter = nextMove
    return nextMove


# TODO there could be issues where these are set while the internet is down (as checked in thread_time), would miss an update if it is
def stream_handler(message):
    try:
        if message["path"].startswith("/schedule"):
            newVal = firebaseConnection.getFirebaseValue("schedule")
            logging.info("firebase: schedule has new value: " + str(newVal))
            getFirebaseValuesAndSetDefaultsIfNeeded()
        if message["path"] == "/setButtonLed":
            newVal = firebaseConnection.getFirebaseValue("setButtonLed")
            logging.info(
                "firebase: setButtonLed has new value: " + str(newVal))
            if(newVal == "on"):
                setButtonLedOn(True)
            if(newVal == "off"):
                setButtonLedOn(False)
            firebaseConnection.setFirebaseValue("setButtonLed", False)
        if message["path"] == "/moveNowOuter":
            newVal = firebaseConnection.getFirebaseValue("moveNowOuter")
            logging.info(
                "firebase: moveNowOuter has new value: " + str(newVal))
            if(bool(newVal)):
                logging.info(
                    "we should move outer now, setting moveNowOuter to false before moving to avoid multiple triggers")
                firebaseConnection.setFirebaseValue("moveNowOuter", False)
                move_stepper_outer()
        if message["path"] == "/moveNowInner":
            newVal = firebaseConnection.getFirebaseValue("moveNowInner")
            logging.info(
                "firebase: moveNowInner has new value: " + str(newVal))
            if(bool(newVal)):
                logging.info(
                    "we should move outer now, setting moveNowInner to false before moving to avoid multiple triggers")
                firebaseConnection.setFirebaseValue("moveNowInner", False)
                move_stepper_inner()
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
            time.sleep(delay)
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_button    : exiting")


def thread_ir_sensor(name):
    global stopMoving

    lastBlack = 0
    lastWhite = 0

    while not exitapp:
        try:
            if GPIO.input(irSensorPin) == GPIO.LOW:
                lastWhite = time.time()
            else:
                lastBlack = time.time()

            if(lastWhite > lastBlack and lastWhite - lastBlack < 0.05 and stopMoving == False):  # just turned white
                stopMoving = True
                logging.info("thread_ir_sensor    : stopMoving")
            time.sleep(delay)
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


if __name__ == '__main__':

    try:
        timestampNow = time.time()
        timeGreenButtonPushed = timestampNow + 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((googleHostForInternetCheck, 0))
        box.boxSettings.ipAddress = s.getsockname()[0]
        box.boxSettings.hostname = socket.gethostname()
        firebaseConnection.setFirebaseValue("ipAddress", box.boxSettings.ipAddress)
        firebaseConnection.setFirebaseValue("hostname", box.boxSettings.hostname)
        firebaseConnection.setFirebaseValue("version", box.boxSettings.version)
        logging.info("next move today of inner is " +
                     str(getNextMove("inner")))
        logging.info("next move today of outer is " +
                     str(getNextMove("outer")))

        latestVersionAvailable = firebaseConnection.getBoxLatestVersion()
        if(box.boxSettings.version != latestVersionAvailable):
            if(latestVersionAvailable == "unknown"):
                logging.error("unable to get latest_version from firebase")
            else:
                logging.warning(
                    "our version [" + box.boxSettings.version + "] latest_version [" + latestVersionAvailable + "]")
        else:
            logging.info(
                "OK our version [" + box.boxSettings.version + "] latest_version [" + latestVersionAvailable + "]")

        buttonThread = threading.Thread(target=thread_button, args=(1,))
        buttonThread.start()
        logging.info("Main    : thread_button started")

        irThread = threading.Thread(target=thread_ir_sensor, args=(1,))
        irThread.start()
        logging.info("Main    : thread_ir_sensor started")

        timeThread = threading.Thread(target=thread_time, args=(1,))
        timeThread.start()
        logging.info("Main    : time thread stared")

        setupStreamToFirebase()

        moveThreadInner = threading.Thread(target=thread_move_inner, args=(1,))
        moveThreadInner.start()
        logging.info("Main    : thread_move_inner stared")

        moveThreadOuter = threading.Thread(target=thread_move_outer, args=(1,))
        moveThreadOuter.start()
        logging.info("Main    : thread_move_outer stared")

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
