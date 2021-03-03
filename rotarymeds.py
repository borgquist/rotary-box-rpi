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


folderPath = '/home/pi/'
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

innerCircle = BoxCircle("innerCircle")
outerCircle = BoxCircle("outerCircle")
boxState = BoxState()

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
chanListInner = [stepper_inner_in1, stepper_inner_in2, stepper_inner_in3, stepper_inner_in4]

stepper_outer_in1 = pinConfigToBeLoaded['stepper_outer_in1']
stepper_outer_in2 = pinConfigToBeLoaded['stepper_outer_in2']
stepper_outer_in3 = pinConfigToBeLoaded['stepper_outer_in3']
stepper_outer_in4 = pinConfigToBeLoaded['stepper_outer_in4']
chanListOuter = [stepper_outer_in1, stepper_outer_in2, stepper_outer_in3, stepper_outer_in4]

led_pin = pinConfigToBeLoaded['led_pin']

boxState.version = "1.0.23"
logging.info("version is " + boxState.version)

googleHostForInternetCheck = "8.8.8.8"


def getserial():
    # Extract serial from cpuinfo file
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

logging.info("CPU serial is [" + str(boxState.cpuId) + "]")


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
boxState.ipAddress = s.getsockname()[0]
boxState.hostname = socket.gethostname()

logging.info("have internet connectivity")

logging.info("Creating FirebaseConnection")
firebaseConnection = FirebaseConnection(str(boxState.cpuId))
logging.info("Done creating FirebaseConnection")

def getFirebaseValuesAndSetDefaultsIfNeeded():

    getSchedules()

    defaultstepperInner = {"name": "inner", "minMove": 2000, "maxMove": 2500, "afterTrigger": 1360, "chanList": chanListInner} 
    innerStepSettnigs = firebaseConnection.getFirebaseValue("stepper",  defaultstepperInner, "innerCircle", "settings")
    innerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 4, "innerCircle", "settings")
    innerCircle.settings.stepper.name = "inner"
    innerCircle.settings.stepper.afterTrigger = innerStepSettnigs["afterTrigger"]
    innerCircle.settings.stepper.maxMove = innerStepSettnigs["maxMove"]
    innerCircle.settings.stepper.minMove = innerStepSettnigs["minMove"]
    innerCircle.settings.stepper.chanList = innerStepSettnigs["chanList"]  # GPIO ports to use
    
    defaultstepperOuter = {"name": "outer", "minMove": 2100, "maxMove": 2900, "afterTrigger": 1640, "chanList": chanListOuter} 
    outerStepSettnigs = firebaseConnection.getFirebaseValue("stepper",  defaultstepperOuter, "outerCircle", "settings")
    outerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 3, "outerCircle", "settings")
    outerCircle.settings.stepper.name = "outer"
    outerCircle.settings.stepper.afterTrigger = outerStepSettnigs["afterTrigger"]
    outerCircle.settings.stepper.maxMove = outerStepSettnigs["maxMove"]
    outerCircle.settings.stepper.minMove = outerStepSettnigs["minMove"]
    outerCircle.settings.stepper.chanList = outerStepSettnigs["chanList"]  # GPIO ports to use
    
    defaultLatestMove = {
        "totalSteps": 0,
        "irTriggered": False,
        "stepsAfterTrigger": 0,
        "timestamp": "1900-01-01 00:00:00",
    }

    innerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", defaultLatestMove, "innerCircle", "state")
    innerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "innerCircle", "state")

    outerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", defaultLatestMove, "outerCircle", "state")
    outerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "outerCircle", "state")
    logging.info("firebase values loaded for innerCircle " + str(innerCircle))
    logging.info("firebase values loaded for outerCircle " + str(outerCircle))
    
    

def getSchedules():
    defaultSchedule =[{"day": "everyday", "hour":7, "minute":0}]
    innerCircle.settings.schedule = firebaseConnection.getFirebaseValue('schedule', defaultSchedule, "innerCircle", "settings")
    outerCircle.settings.schedule = firebaseConnection.getFirebaseValue('schedule', defaultSchedule, "outerCircle", "settings")

getFirebaseValuesAndSetDefaultsIfNeeded()

firebaseConnection.setFirebaseValue("setButtonLed", False, "commands")

firebaseConnection.setFirebaseValue("moveNow", False, "innerCircle", "commands")
firebaseConnection.setFirebaseValue("setPocketsFull", False, "innerCircle", "commands")

firebaseConnection.setFirebaseValue("moveNow", False, "outerCircle", "commands")
firebaseConnection.setFirebaseValue("setPocketsFull", False, "outerCircle", "commands")

exitapp = False
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_led_pin, GPIO.OUT)
GPIO.setup(button_pushed_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(led_pin, GPIO.OUT)
GPIO.output(led_pin, GPIO.LOW)
GPIO.setup(ir_pin, GPIO.IN)


# initialize array for sequence shift
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
    logging.info("move_stepper called for " + circle.name + " with settings " + str(circle.settings.stepper))
    
    while (moveIsBeingDone):
        logging.info(circle.name + " : waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move(circle)
    circle.state.pocketsFull = max(circle.state.pocketsFull -1, 0)
    firebaseConnection.setFirebaseValue("pocketsFull", circle.state.pocketsFull, circle.name, "state")
    moveIsBeingDone = False

    

def holdBothMotors():
    global arr1  # enables the edit of arr1 var inside a function
    arrOUT = arr1[1:]+arr1[:1]  # rotates array values of 1 digi
    GPIO.output(innerCircle.settings.stepper.chanList, arrOUT)
    GPIO.output(outerCircle.settings.stepper.chanList, arrOUT)


def releaseBothMotors():
    global arrOff
    GPIO.output(innerCircle.settings.stepper.chanList, arrOff)
    GPIO.output(outerCircle.settings.stepper.chanList, arrOff)


irTriggered = False

def move(circle: BoxCircle):
    logging.info("move called for " + str(circle))
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

    logMessage = circle.name + " totalSteps [" + str(stepsDone) + "] irTriggered [" + str(irTriggered) + "] stepsAfterTrigger [" + str(stepsDone - stepsDoneWhenIRtrigger) + "]"
    logging.info("move    : " + logMessage)
    now = datetime.datetime.now()

    latestMove = {
        "totalSteps": stepsDone,
        "irTriggered": irTriggered,
        "stepsAfterTrigger": stepsDone - stepsDoneWhenIRtrigger,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
    }

    circle.state.latestMove = latestMove
    firebaseConnection.setFirebaseValue("latestMove", latestMove, circle.name, "state")
    
    GPIO.output(circle.settings.stepper.chanList, arrOff)
    setButtonLedOn(True)
    releaseBothMotors()


boxState.buttonLedOn = True
def setButtonLedOn(setToOn):
    if(setToOn):
        logging.info("setButtonLedOn    : turning ON the buttonLed")
        boxState.buttonLedOn = True
        GPIO.output(button_led_pin, GPIO.HIGH)
        GPIO.output(led_pin, GPIO.HIGH)
        firebaseConnection.setFirebaseValue("buttonLedOn", True, "state")

    else:
        logging.info("setButtonLedOn    : turning OFF the buttonLed")
        boxState.buttonLedOn = False
        GPIO.output(button_led_pin, GPIO.LOW)
        GPIO.output(led_pin, GPIO.LOW)
        firebaseConnection.setFirebaseValue("buttonLedOn", False, "state")


def getNextMove(schedule):
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



def checkCommandMoveNow(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue("moveNow", False, circle.name, "commands")
    if(bool(newVal)):
        logging.info("moveNow true for " + str(circle))
        firebaseConnection.setFirebaseValue("moveNow", False, circle.name, "commands")
        move_stepper(circle)

def checkCommandsPockets(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue("setPocketsFull", False, circle.name, "commands")
    if(newVal != False):
        logging.info(circle.name + " setPocketsFull called to be updated to " + str(int(newVal)))
        firebaseConnection.setFirebaseValue("setPocketsFull", False, circle.name, "commands")
        firebaseConnection.setFirebaseValue("pocketsFull", int(newVal), circle.name, "state")
        circle.state.pocketsFull = int(newVal)
        

def checkCommandsNodes():
    logging.info("checkCommandsNodes called")
    checkCommandSetButtonLed()
    checkCommandMoveNow(innerCircle)
    checkCommandMoveNow(outerCircle)
    checkCommandsPockets(innerCircle)
    checkCommandsPockets(outerCircle)
    

# TODO there could be issues where these are set while the internet is down (as checked in thread_time), would miss an update if it is
def stream_handler(message):
    try:
        if message["path"].startswith("/commands/innerCircle/settings/schedule"):
            newVal = firebaseConnection.getFirebaseValue("schedule", None, "innerCircle", "settings")
            logging.info("firebase: schedule for innerCircle has new value: " + str(newVal))
            getSchedules()
        if message["path"].startswith("/commands/outerCircle/settings/schedule"):
            newVal = firebaseConnection.getFirebaseValue("schedule", None, "outerCircle", "settings")
            logging.info("firebase: schedule for outerCircle has new value: " + str(newVal))
            getSchedules()
        if message["path"].startswith("/commands/innerCircle/settings/stepper"):
            newVal = firebaseConnection.getFirebaseValue("stepper", None, "innerCircle", "settings")
            logging.info("firebase: stepper for innerCircle has new value: " + str(newVal))
            getFirebaseValuesAndSetDefaultsIfNeeded()
        if message["path"].startswith("/commands/outerCircle/settings/stepper"):
            newVal = firebaseConnection.getFirebaseValue("stepper", None, "outerCircle", "settings")
            logging.info("firebase: stepper for outerCircle has new value: " + str(newVal))
            getFirebaseValuesAndSetDefaultsIfNeeded()
        if message["path"] == "/commands/setButtonLed":
            newVal = firebaseConnection.getFirebaseValue("setButtonLed", None, "commands")
            logging.info("firebase: /commands/setButtonLed new value: " + str(newVal))
            checkCommandSetButtonLed()
        if message["path"] == "/commands/innerCircle/moveNow":
            newVal = firebaseConnection.getFirebaseValue("moveNow", None, "innerCircle", "commands")
            logging.info("firebase: /commands/innerCircle/moveNow new value: " + str(newVal))
            checkCommandMoveNow(innerCircle)
        if message["path"] == "/commands/outerCircle/moveNow":
            newVal = firebaseConnection.getFirebaseValue("moveNow", None, "outerCircle", "commands")
            logging.info("firebase: /commands/outerCircle/moveNow has new value: " + str(newVal))
            checkCommandMoveNow(outerCircle)
        if message["path"] == "/commands/innerCircle/setPocketsFull":
            newVal = firebaseConnection.getFirebaseValue("setPocketsFull", None, "innerCircle", "commands")
            logging.info("firebase: /commands/innerCircle/setPocketsFull has new value: " + str(newVal))
            checkCommandsPockets(innerCircle)
        if message["path"] == "/commands/outerCircle/setPocketsFull":
            newVal = firebaseConnection.getFirebaseValue("setPocketsFull", None, "outerCircle", "commands")
            logging.info("firebase: /commands/outerCircle/setPocketsFull has new value: " + str(newVal))
            checkCommandsPockets(outerCircle)
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

            if(timestampNow - lastTimeStampUpdate > pingSeconds and timestampNow - lastTimeStampUpdate > 60):
                firebaseConnection.setPing()
                lastTimeStampUpdate = timestampNow

        except Exception as err:
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_time    : exiting")


def thread_move(circle: BoxCircle):
    lastMove = datetime.datetime.now() + datetime.timedelta(days=-1)

    while not exitapp:
        try:
            currentCachedValue = circle.state.nextMove
            nextMove = getNextMove(circle.settings.schedule)
            
            if(str(nextMove) != str(currentCachedValue)):
                firebaseConnection.setFirebaseValue("nextMove", str(nextMove).strip(), circle.name, "state")
                circle.state.nextMove = nextMove

            if(nextMove != 0):
                now = datetime.datetime.now()

                secondsBetween = abs((now-nextMove).total_seconds())

                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info(
                        "thread_move" + circle.name + "    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logging.info(
                            "thread_move" + circle.name + "    :  it's time to move!")
                        lastMove = now
                        move_stepper(circle)
        except Exception as err:
            logging.error("exception " + traceback.format_exc())

        time.sleep(5)

    logging.info("thread_move" + circle.name + "    :   exiting")

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
                    logging.info(
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
            logging.error("exception " + traceback.format_exc())

    logging.info("thread_button    : exiting")


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
    my_stream = firebaseConnection.database.child("box").child("boxes").child(boxState.cpuId).stream(stream_handler)
    logging.info("done setting up the stream to firebase")
    checkCommandsNodes()




if __name__ == '__main__':

    try:
        timestampNow = time.time()
        timeGreenButtonPushed = timestampNow + 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)

        firebaseConnection.setFirebaseValue("cpuId", boxState.cpuId, "state")
        firebaseConnection.setFirebaseValue("ipAddress", boxState.ipAddress, "state")
        firebaseConnection.setFirebaseValue("hostname", boxState.hostname, "state")
        firebaseConnection.setFirebaseValue("version", boxState.version, "state")
        
        latestVersionAvailable = firebaseConnection.getBoxLatestVersion()
        pingSeconds = int(firebaseConnection.getPingSeconds())

        if(boxState.version != latestVersionAvailable):
            if(latestVersionAvailable == "unknown"):
                logging.error("unable to get latest_version from firebase")
            else:
                logging.warning(
                    "our version [" + boxState.version + "] latest_version [" + latestVersionAvailable + "]")
        else:
            logging.info(
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
