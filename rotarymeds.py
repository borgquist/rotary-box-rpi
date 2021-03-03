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
boxState.version = "1.0.24"
logging.info("version is " + boxState.version)

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
logging.info("CPU serial is [" + str(boxState.cpuId) + "]")

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

logging.info("checking internet connectivity")
while(not haveInternet()):
    logging.info("internet is not available, sleeping 1 second")
    time.sleep(1)
logging.info("have internet connectivity")

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.connect((googleHostForInternetCheck, 0))
boxState.ipAddress = s.getsockname()[0]
boxState.hostname = socket.gethostname()

logging.info("Creating FirebaseConnection")
firebaseConnection = FirebaseConnection(str(boxState.cpuId))
logging.info("Done creating FirebaseConnection")

defaultstepperInner = {"minMove": 2000, "maxMove": 2500, "afterTrigger": 1360, "chanList": chanListInner} 
defaultstepperOuter = {"minMove": 2100, "maxMove": 2900, "afterTrigger": 1640, "chanList": chanListOuter} 
defaultLatestMove = {
    "totalSteps": 0,
    "irTriggered": False,
    "stepsAfterTrigger": 0,
    "timestamp": "1900-01-01 00:00:00",
    }

def getFirebaseValuesAndSetDefaultsIfNeeded():
    getSchedules()
    innerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 7, "settings", innerCircle.name)
    getStepper(innerCircle, defaultstepperInner)
    outerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 7, "settings", outerCircle.name)
    getStepper(outerCircle, defaultstepperOuter)
    innerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", defaultLatestMove, "state", innerCircle.name)
    innerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "state", innerCircle.name)
    outerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", defaultLatestMove, "state", outerCircle.name)
    outerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "state", outerCircle.name)

def getStepper(circle: BoxCircle, defaultstepper):
    firebaseStepSettings = firebaseConnection.getFirebaseValue("stepper",  defaultstepper, "settings", circle.name)
    circle.settings.stepper.afterTrigger = firebaseStepSettings["afterTrigger"]
    circle.settings.stepper.maxMove = firebaseStepSettings["maxMove"]
    circle.settings.stepper.minMove = firebaseStepSettings["minMove"]
    circle.settings.stepper.chanList = firebaseStepSettings["chanList"]

def getSchedules():
    defaultSchedule =[{"day": "everyday", "hour":7, "minute":0}]
    innerCircle.settings.schedule = firebaseConnection.getFirebaseValue('schedule', defaultSchedule, "settings", innerCircle.name)
    outerCircle.settings.schedule = firebaseConnection.getFirebaseValue('schedule', defaultSchedule, "settings", outerCircle.name)

getFirebaseValuesAndSetDefaultsIfNeeded()

firebaseConnection.setFirebaseValue("setButtonLed", False, "commands")
firebaseConnection.setFirebaseValue("moveNow", False, "commands", innerCircle.name)
firebaseConnection.setFirebaseValue("setPocketsFull", False, "commands", innerCircle.name)
firebaseConnection.setFirebaseValue("moveNow", False, "commands", outerCircle.name)
firebaseConnection.setFirebaseValue("setPocketsFull", False, "commands", outerCircle.name)

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
        logging.info(circle.name + " : waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move(circle)
    circle.state.pocketsFull = max(circle.state.pocketsFull -1, 0)
    firebaseConnection.setFirebaseValue("pocketsFull", circle.state.pocketsFull, "state", circle.name)
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
    logging.info("move called for " + str(circle))
    global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
    stepsDone = 0
    holdBothMotors()
    stepsDoneWhenIRtrigger = 0
    irTriggered = False
    
    def oneStep(stepsDone):
        global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
        arrOUT = arr1[3:]+arr1[:3]  #  arrOUT = arr1[1:]+arr1[:1] for counterclockwise
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
        "timestamp": datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }
    logging.info("move complete    : " + circle.name + str(latestMove))
    circle.state.latestMove = latestMove
    firebaseConnection.setFirebaseValue("latestMove", latestMove, "state", circle.name)
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
    newVal = firebaseConnection.getFirebaseValue("moveNow", False, "commands", circle.name)
    if(bool(newVal)):
        logging.info("moveNow true for " + str(circle))
        firebaseConnection.setFirebaseValue("moveNow", False, "commands", circle.name)
        move_stepper(circle)

def checkCommandsPockets(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue("setPocketsFull", False, "commands", circle.name)
    if(newVal != False):
        logging.info(circle.name + " setPocketsFull called to be updated to " + str(int(newVal)))
        firebaseConnection.setFirebaseValue("setPocketsFull", False, "commands", circle.name)
        firebaseConnection.setFirebaseValue("pocketsFull", int(newVal), "state", circle.name)
        circle.state.pocketsFull = int(newVal)
        
def checkCommandsNodes():
    logging.info("checkCommandsNodes called")
    checkCommandSetButtonLed()
    checkCommandMoveNow(innerCircle)
    checkCommandMoveNow(outerCircle)
    checkCommandsPockets(innerCircle)
    checkCommandsPockets(outerCircle)
    
def stream_handler(message):
    try:
        path = "/innerCircle/settings/schedule"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue("schedule", None, "settings", innerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            getSchedules()
        path = "/outerCircle/settings/schedule"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue("schedule", None, "settings", outerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            getSchedules()
        path = "/innerCircle/settings/stepper"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue("stepper", None, "settings", innerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            getStepper(innerCircle, defaultstepperInner)
        path = "/outerCircle/settings/stepper"
        if message["path"].startswith(path):
            newVal = firebaseConnection.getFirebaseValue("stepper", None, "settings", outerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            getStepper(outerCircle, defaultstepperOuter)
        path = "/commands/setButtonLed"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue("setButtonLed", None, "commands")
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            checkCommandSetButtonLed()
        path = "/innerCircle/commands/moveNow"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue("moveNow", None, "commands", innerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            checkCommandMoveNow(innerCircle)
        path = "/outerCircle/commands/moveNow"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue("moveNow", None, "commands", outerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            checkCommandMoveNow(outerCircle)
        path = "/innerCircle/commands/setPocketsFull"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue("setPocketsFull", None, "commands", innerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
            checkCommandsPockets(innerCircle)
        path = "/outerCircle/commands/setPocketsFull"
        if message["path"] == path:
            newVal = firebaseConnection.getFirebaseValue("setPocketsFull", None, "commands", outerCircle.name)
            logging.info("firebase: " + path + " has new value: " + str(newVal))
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
                firebaseConnection.setFirebaseValue("nextMove", str(nextMove).strip(), "state", circle.name)
                circle.state.nextMove = nextMove

            if(nextMove != 0):
                now = datetime.datetime.now()
                secondsBetween = abs((now-nextMove).total_seconds())
                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info("thread_move" + circle.name + "    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logging.info("thread_move" + circle.name + "    :  it's time to move!")
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
                    logging.info("thread_button    : button_pushed_pin button was pushed!")
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