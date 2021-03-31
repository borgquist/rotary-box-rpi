from latestmove import LatestMove
from commands import Commands
from schedule import Schedule
from utilityfunctions import UtilityFunctions
from pyrebase import Stream
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

def getFirebaseValuesAndSetDefaultsIfNeeded():
    getTimezone()
    getSchedules()
    innerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 7, "settings", innerCircle.name,"circles")
    getStepper(innerCircle, defaultstepperInner)
    outerCircle.settings.nrPockets = firebaseConnection.getFirebaseValue("nrPockets", 7, "settings", outerCircle.name,"circles")
    getStepper(outerCircle, defaultstepperOuter)
    innerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", LatestMove().getDict(), "state", innerCircle.name,"circles")
    innerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "state", innerCircle.name,"circles")
    outerCircle.state.latestMove = firebaseConnection.getFirebaseValue("latestMove", LatestMove().getDict(), "state", outerCircle.name,"circles")
    outerCircle.state.pocketsFull = firebaseConnection.getFirebaseValue("pocketsFull", 0, "state", outerCircle.name,"circles")

def getTimezone():
    boxSettings.timezone = firebaseConnection.getFirebaseValue("timezone", "Europe/London", "settings")

def getStepper(circle: BoxCircle, defaultstepper):
    firebaseStepSettings = firebaseConnection.getFirebaseValue(
        "stepper",  defaultstepper, "settings", circle.name, "circles")
    circle.settings.stepper.afterTrigger = firebaseStepSettings["afterTrigger"]
    circle.settings.stepper.maxMove = firebaseStepSettings["maxMove"]
    circle.settings.stepper.minMove = firebaseStepSettings["minMove"]
    circle.settings.stepper.chanList = firebaseStepSettings["chanList"]

def getSchedules():
    innerSchedules = []
    orderedDictInner = firebaseConnection.getFirebaseValue('schedules', {UtilityFunctions.generateId():Schedule().getDict()}, "settings", innerCircle.name, "circles")
    for key in orderedDictInner:
        innerSchedules.append(orderedDictInner[key])
    innerCircle.settings.schedules = innerSchedules
    time.sleep(0.01) # want to make sure they don't get the same id
    outerSchedules = []
    orderedDictOuter = firebaseConnection.getFirebaseValue('schedules', {UtilityFunctions.generateId():Schedule().getDict()}, "settings", outerCircle.name, "circles")
    for key in orderedDictOuter:
        outerSchedules.append(orderedDictOuter[key])
    outerCircle.settings.schedules = outerSchedules


def move_stepper(circle: BoxCircle):
    global moveIsBeingDone
    while (moveIsBeingDone):
        logger.info("[" + circle.name + "] : waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move(circle)
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

def move(circle: BoxCircle):
    logger.info("called for " + str(circle.name))
    global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
    totalSteps = 0
    holdBothMotors()
    stepsDoneWhenIRtrigger = 0
    irTriggered = False

    def oneStep(totalSteps) -> int:
        global irTriggered, stepsDoneWhenIRtrigger, arr1, arr2
        # arrOUT = arr1[1:]+arr1[:1] for counterclockwise
        arrOUT = arr1[3:]+arr1[:3]
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(circle.settings.stepper.chanList, arrOUT)
        time.sleep(0.0012)
        if irTriggered and stepsDoneWhenIRtrigger == 0:
            stepsDoneWhenIRtrigger = totalSteps
        return totalSteps + 1
    while totalSteps < circle.settings.stepper.minMove:
        totalSteps = oneStep(totalSteps)
    while totalSteps < stepsDoneWhenIRtrigger + circle.settings.stepper.afterTrigger and totalSteps < circle.settings.stepper.maxMove:
        totalSteps = oneStep(totalSteps)
    while irTriggered == False and totalSteps < circle.settings.stepper.maxMove:
        totalSteps = oneStep(totalSteps)

    releaseBothMotors()
    
    latestMove = {
        "totalSteps": totalSteps,
        "irTriggered": irTriggered,
        "stepsAfterTrigger": totalSteps - stepsDoneWhenIRtrigger,
        "timestamp": DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone).strftime(DateTimeFunctions.fmt),
        "timestampEpoch": time.time(),
        "timeStr": DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone).strftime(DateTimeFunctions.fmt_time),
        "minutesSincePod": 0,
    }
    logger.info("complete for " + circle.name + str(latestMove))
    circle.state.latestMove = latestMove
    firebaseConnection.setFirebaseValue("latestMove", latestMove, "state", circle.name, "circles")
    
    setButtonLed(True)
    setMoveAwaitingConfirmationForCircle(circle)
    circle.state.pocketsFull = max(circle.state.pocketsFull - 1, 0)
    firebaseConnection.setFirebaseValue("pocketsFull", circle.state.pocketsFull, "state", circle.name, "circles")

def getNextMove(schedules) -> datetime.datetime:
    nextMove = None
    for schedule in schedules:
        candiate = DateTimeFunctions.getDateTimeFromScheduleWithTimezone(
            schedule['day'], schedule['dayType'], schedule['hour'], schedule['minute'], boxSettings.timezone)
        if(candiate is not None):
            if(nextMove == None):
                nextMove = candiate
            elif(nextMove > candiate):
                nextMove = candiate
    return nextMove

def parseButtonLedStringReturnLedOn(buttonStr) -> bool:
    if(buttonStr[:2] == "on"):
        return True
    if(buttonStr[:3] == "off"):
        return False
    return False

def checkCommandSetButtonLed():
    newVal = firebaseConnection.getFirebaseValue("setButtonLed", False, "commands")
    if(bool(newVal) is False):
        return
    logger.info(
        "setButtonLed has new value: " + str(newVal))
    ledOn = parseButtonLedStringReturnLedOn(str(newVal))
    setButtonLed(ledOn, True)
    
def setButtonLed(ledOn: bool, clearCommands: bool = False):
    while(internetIsAvailable == False):
        time.sleep(1)
        logger.info("sleeping setButtonLed due to internetIsAvailable")
    if(ledOn):
        boxState.buttonLedOn = True
        GPIO.output(button_led_pin, GPIO.HIGH)
        GPIO.output(led_pin, GPIO.HIGH)
        firebaseConnection.setFirebaseValue("buttonLedOn", True, "state")
    else:
        boxState.buttonLedOn = False
        GPIO.output(button_led_pin, GPIO.LOW)
        GPIO.output(led_pin, GPIO.LOW)
        firebaseConnection.setFirebaseValue("buttonLedOn", False, "state")
        resetMoveAwaitingConfirmation()

    if(clearCommands):
        firebaseConnection.setFirebaseValue("setButtonLed", False,  "commands")

def setMoveAwaitingConfirmationForCircle(circle: BoxCircle):
    circle.state.moveAwaitingConfirmation = True
    logger.info("have set moveAwaitingConfirmation to True for " + circle.name)

def resetMoveAwaitingConfirmation():
    if(innerCircle.state.moveAwaitingConfirmation):
        logger.info("resetting moveAwaitingConfirmation for innerCircle")
        innerCircle.state.moveAwaitingConfirmation = False
    
    if(outerCircle.state.moveAwaitingConfirmation):
        logger.info("resetting moveAwaitingConfirmation for outerCircle")
        outerCircle.state.moveAwaitingConfirmation = False
    
def checkCommandMoveNow(circle: BoxCircle, callbackValue: bool = False):
    moveNow = callbackValue
    if(callbackValue == False):
        moveNow = firebaseConnection.getFirebaseValue("moveNow_" + circle.name, False, "commands")
    if(bool(moveNow)):
        logger.info("moveNow true for " + str(circle.name))
        firebaseConnection.setFirebaseValue("moveNow_" + circle.name, False, "commands")
        move_stepper(circle)

def checkCommandsPockets(circle: BoxCircle):
    newVal = firebaseConnection.getFirebaseValue("setPocketsFull_" + circle.name, False, "commands")
    logger.info("called value is [" +str(newVal) + "] for [" + circle.name + "]")
    if(newVal != False):
        logger.info(circle.name + " command setPocketsFull called to be updated to " + str(int(newVal)))
        setPocketsFull(circle, int(newVal), True)

def setPocketsFull(circle: BoxCircle, pocketsFull: int, clearCommands: bool):
    logger.info("called with pocketsFull [" +str(pocketsFull) + "] clearCommands [" + str(clearCommands) + "]")
    if(clearCommands):
        firebaseConnection.setFirebaseValue("setPocketsFull_" + circle.name, False, "commands")

    firebaseConnection.setFirebaseValue("pocketsFull", pocketsFull, "state", circle.name, "circles")
    circle.state.pocketsFull = pocketsFull
        
def checkCommandsJsonData(commandsJson: str):
    if(bool(commandsJson["moveNow_innerCircle"])):
        logger.info("moveNow_innerCircle was true")
        checkCommandMoveNow(innerCircle, True)

    if(bool(commandsJson["moveNow_outerCircle"])):
        logger.info("moveNow_outerCircle was true")
        checkCommandMoveNow(outerCircle, True)

    if(bool(commandsJson["doRestart"])):
        logger.info("doRestart was true")
        doRestartWithGitclone()

    if(str(commandsJson["setButtonLed"]).lower() != "false"):
        logger.info("ping was [" + str(commandsJson["setButtonLed"]) +"]")
        checkCommandSetButtonLed()

    if(str(commandsJson["setPocketsFull_innerCircle"]).lower() != "false"):
        logger.info("setPocketsFull_innerCircle was [" + str(commandsJson["setPocketsFull_innerCircle"]) +"]")
        checkCommandsPockets(innerCircle)

    if(str(commandsJson["setPocketsFull_outerCircle"]).lower() != "false"):
        logger.info("setPocketsFull_outerCircle was [" + str(commandsJson["setPocketsFull_outerCircle"]) +"]")
        checkCommandsPockets(outerCircle)

def stream_handler(message):
    global pingTimestampFromStream
    try:
        data = message["data"]
        if message["path"] == '/':
            checkCommandsJsonData(data["commands"])
            return
        
        if message["path"] == '/ping':
            if(int(data) > pingTimestampFromStream):
                pingTimestampFromStream = int(data) 
            else:
                logger.info("ignoring ping since it is from last time the box was running")
            return

        if message["path"] == '/settings/timezone':
            logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
            boxSettings.timezone = str(data)
            firebaseConnection.setPing()
            updateFirebaseWithNextMove(innerCircle, getNextMove(innerCircle.settings.schedules))
            updateFirebaseWithNextMove(outerCircle, getNextMove(outerCircle.settings.schedules))
            return

        if str(message["path"]).startswith('/circles/innerCircle/settings/schedules'):
            logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
            getSchedules()
            updateFirebaseWithNextMove(innerCircle, getNextMove(innerCircle.settings.schedules))
            return

        if str(message["path"]).startswith('/circles/outerCircle/settings/schedules'):
            logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
            getSchedules()
            updateFirebaseWithNextMove(outerCircle, getNextMove(outerCircle.settings.schedules))
            return

        if str(message["path"]).startswith('/circles/innerCircle/settings/stepper'):
            logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
            getStepper(innerCircle, defaultstepperInner)
            return

        
        if str(message["path"]).startswith('/circles/outerCircle/settings/stepper'):
            logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
            getStepper(outerCircle, defaultstepperOuter)
            return

        if message["path"] == '/commands/setButtonLed':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                ledOn = parseButtonLedStringReturnLedOn(str(data))
                setButtonLed(ledOn, True)
            return
        
        if message["path"] == '/commands/moveNow_innerCircle':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                checkCommandMoveNow(innerCircle, bool(data))
            return

        if message["path"] == '/commands/moveNow_outerCircle':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                checkCommandMoveNow(outerCircle, bool(data))
            return
            

        if message["path"] == '/commands/setPocketsFull_innerCircle':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                if(data == "empty"):
                    setPocketsFull(innerCircle, 0, True)    
                else:
                    setPocketsFull(innerCircle, int(data), True)
            return

        if message["path"] == '/commands/setPocketsFull_outerCircle':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                if(data == "empty"):
                    setPocketsFull(outerCircle, 0, True)    
                else:
                    setPocketsFull(outerCircle, int(data), True)
            return
        
        if message["path"] == '/commands/doRestart':
            if(data != False):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                firebaseConnection.setFirebaseValue("doRestart", False, "commands")
                doRestartWithGitclone()
            return

        if message["path"] == '/commands/ping':
            if(data == True or data == 'ping'):
                logger.info("path  [" + message["path"] + "] received with data [" + str(data) + "]")
                firebaseConnection.setFirebaseValue("ping", time.time(), "commands")
            return

        logger.info("we're ignoring the callback for  [" + message["path"] + "] received with data [" + str(data) + "]")
            
    except Exception as err:
        logging.error("exception in stream_handler " + str(err) + " trace: " + traceback.format_exc())


def thread_ping(name):
    lastPingSent = 0
    sleepSeconds = 5
    while not exitapp:
        try:
            time.sleep(sleepSeconds)
            timestampNow = time.time()
            if(internetIsAvailable):
                if(timestampNow - lastPingSent > pingSeconds):
                    firebaseConnection.setPing()
                    lastPingSent = timestampNow
            else:
                logger.info("not setting ping since internet is not available")
        except requests.exceptions.HTTPError as e:
           logging.error("HTTPError [" + str(e).replace('\n', ' ').replace('\r', '') +"]")
        
        except Exception as err:
            logging.error("exception " + str(err) + " trace :" + traceback.format_exc())
    logger.info("exiting")

def updateFirebaseWithNextMove(circle: BoxCircle, nextMove: datetime.datetime):
    if(str(nextMove) != str(circle.state.nextMove)):
        logger.info("nextMove needs updating from [" + str(circle.state.nextMove) + "] to [" + str(nextMove) +"] for " + circle.name)
        firebaseConnection.setFirebaseValue("nextMove", str(nextMove).strip(), "state", circle.name, "circles")
        circle.state.nextMove = nextMove

    if(nextMove is None):
        nextMoveInEpoch = None
    else:
        nextMoveInEpoch = nextMove.timestamp()

    if(str(nextMoveInEpoch) != str(circle.state.nextMoveInEpoch)):
        logger.info("nextMoveInEpoch needs updating from [" + str(circle.state.nextMoveInEpoch) + "] to [" + str(nextMoveInEpoch) +"]  for " + circle.name)
        if(nextMoveInEpoch is not None):
            nextMoveInEpoch = float(nextMoveInEpoch)
        firebaseConnection.setFirebaseValue("nextMoveInEpoch", nextMoveInEpoch, "state", circle.name, "circles")
        circle.state.nextMoveInEpoch = nextMoveInEpoch

def thread_move(circle: BoxCircle):
    lastMove = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone) - datetime.timedelta(days=-1)
    global internetIsAvailable
    sleepSeconds = 5
    nextMove = None
    while not exitapp:
        try:
            time.sleep(sleepSeconds)
            nextMove = getNextMove(circle.settings.schedules)
    
            if(internetIsAvailable):
                updateFirebaseWithNextMove(circle, nextMove)
            
            if(nextMove is not None):
                now = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
                secondsBetween = abs((now-nextMove).total_seconds())
                if(abs((now-lastMove).total_seconds()) < 60):
                    logger.info("[" + circle.name + "] moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20):
                        logger.info("[" + circle.name + "] it's time to move!")
                        lastMove = DateTimeFunctions.getDateTimeNowNormalized(boxSettings.timezone)
                        move_stepper(circle)
            
            if(circle.state.moveAwaitingConfirmation):
                checkMinutesSincePod(circle)

        except requests.exceptions.HTTPError as e:
            logging.error("HTTPError [" + str(e).replace('\n', ' ').replace('\r', '') +"]")
        except Exception as err:
            logging.error("exception: [" + str(err) + "] the trace: [" + traceback.format_exc() + "]")
        
    logger.info(circle.name + "    :   exiting")

def checkTime(circle: BoxCircle, minSinceMove: int, alertMinutes: int) -> bool: 
    if(minSinceMove < alertMinutes):
        return False
    if(float(circle.state.latestMove['minutesSincePod']) < alertMinutes and minSinceMove >= alertMinutes):
        logger.info("setting minutesSincePod for " + circle.name + " to" + str(alertMinutes))
        circle.state.latestMove['minutesSincePod'] = alertMinutes
        firebaseConnection.setFirebaseValue("minutesSincePod", alertMinutes, "latestMove", "state", circle.name, "circles")
        return True
    return False

def checkMinutesSincePod(circle: BoxCircle):
    timestampEpoch = float(circle.state.latestMove['timestampEpoch'])
    minSinceMove = int((time.time() - timestampEpoch) / 60)
    if(checkTime(circle, minSinceMove, 1)): return
    if(checkTime(circle, minSinceMove, 2)): return
    if(checkTime(circle, minSinceMove, 3)): return
    if(checkTime(circle, minSinceMove, 10)): return
    if(checkTime(circle, minSinceMove, 20)): return
    if(checkTime(circle, minSinceMove, 30)): return
    if(checkTime(circle, minSinceMove, 40)): return
    if(checkTime(circle, minSinceMove, 50)): return
    if(checkTime(circle, minSinceMove, 60)): return
    if(checkTime(circle, minSinceMove, 90)): return
    if(checkTime(circle, minSinceMove, 120)): return
    if(checkTime(circle, minSinceMove, 180)): return
    if(checkTime(circle, minSinceMove, 240)): return
    if(checkTime(circle, minSinceMove, 300)): return
    if(checkTime(circle, minSinceMove, 360)): return
    if(checkTime(circle, minSinceMove, 420)): return
    if(checkTime(circle, minSinceMove, 480)): return
    if(checkTime(circle, minSinceMove, 540)): return
    if(checkTime(circle, minSinceMove, 600)): return
    if(checkTime(circle, minSinceMove, 660)): return
    if(checkTime(circle, minSinceMove, 720)): return


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
                while(internetCheckWaitWhileNotAvailable()):
                    logger.info("waiting with button press command until internet is back")

                timestampNow = time.time()

                if(timeButtonNotPressed > timeButtonPressMostRecent):
                    logger.info(
                        "button_pushed_pin button was pushed!")
                    if(boxState.buttonLedOn):
                        setButtonLed(False)
                    else:
                        setButtonLed(True)
                    timeButtonPressMostRecent = timestampNow
            else:
                timeButtonNotPressed = time.time()
            time.sleep(0.1)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    logger.info("exiting")

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
                    logger.info("irTriggered")
            time.sleep(0.05)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    logger.info("exiting")


def internetCheckWaitWhileNotAvailable():
    internetWasLost = False
    global internetIsAvailable
    global timestampInternetAvailable
    try:    
        while(UtilityFunctions.haveInternet() == False):
            logger.warning("internet is lost")
            internetIsAvailable = False
            internetWasLost = True
            time.sleep(3)

        if(internetWasLost):
            timeLost = time.time() - timestampInternetAvailable
            logger.info("internet is back after " + str(round(timeLost)) + " seconds")
        timestampInternetAvailable = time.time()
        internetIsAvailable = True
    except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())

def firebase_callback_thread(name):
    global pingTimestampFromStream
    sleepSeconds = 5
    
    while not exitapp:
        try:
            timeSinceInternetCheck = time.time() - pingTimestampFromStream
            if(timeSinceInternetCheck > pingSeconds * 2):
                logger.warning("it's been [" + str(round(timeSinceInternetCheck)) + "] seconds since last pingTimestampFromStream resetting it")
                resetFirebaseStreams()
                pingTimestampFromStream = time.time() # this is to avoid us doing many checks in a row if it takes a while to get the connection up again
                firebaseConnection.setPing()
                firebaseConnection.increaseStreamResetCount()
            time.sleep(sleepSeconds)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    logger.info("exiting")

def resetFirebaseStreams():
    global firebase_stream
    internetCheckWaitWhileNotAvailable()
    try:
        if(firebase_stream != ""):
            firebase_stream.close()
    except Exception as err:
        logger.warning("firebase_stream.close() failed " + str(err) + " trace: " + traceback.format_exc())
    firebase_stream = firebaseConnection.database.child("box").child("boxes").child(boxState.cpuId).stream(stream_handler)

    logger.info("Firebase stream reset done")

                                   
def checkVersionAndUpdateIfNeeded():
    if(UtilityFunctions.versionIsLessThanServer(boxState.version, latestVersionAvailable) == False):
        return
    logging.warning("PodQ box needs updating [" + boxState.version + "] latest_version [" + latestVersionAvailable + "] calling doRestartWithGitclone")
    doRestartWithGitclone()
    return

def doRestartWithGitclone():
    logger.info("doRestartWithGitclone called")
    os.system('sudo /home/pi/gitclone.sh')
    logger.info("gitclone complete, calling reboot")
    flashButtonLed(0.2, 20, True)
    os.system('sudo reboot now')
                        
def flashButtonLed(speedInSeconds, nrFlashes, finalValue):
    ledOn = False
    def setButtonLedOn(setToOn):
        if(setToOn):
            GPIO.output(button_led_pin,GPIO.HIGH)
        else:
            GPIO.output(button_led_pin,GPIO.LOW)
    for x in range(int(nrFlashes)):
        ledOn = not ledOn
        setButtonLedOn(ledOn)
        time.sleep(speedInSeconds)
    setButtonLedOn(finalValue)        

if __name__ == '__main__':
    try:
        boxState = BoxState()
        boxState.version = "1.0.2"
        
        exitapp = False
        folderPath = '/home/pi/'
        os.makedirs(folderPath + "logs/", exist_ok=True)
        logFormat = '%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s'
        date_fmt = '%a %d %b %Y %H:%M:%S'
        logging.basicConfig(format=logFormat,
                            datefmt=date_fmt,
                            level=logging.INFO
                            )
        connectionpool_logger = logging.getLogger("requests.packages.urllib3.connectionpool")
        connectionpool_logger.setLevel(logging.WARNING)
        logger = logging.getLogger('podq')
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(folderPath + "logs/podq.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(logFormat, date_fmt)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        logger.info("PodQ starting ---------------------------------------------------")
        wifiDetails = UtilityFunctions.getWifiInfo()
        logger.info("wifi details " + wifiDetails)
        boxState.cpuId = UtilityFunctions.getserial()
        
        boxSettings = BoxSettings()
        pinConfigFilePath = '/home/pi/pinlayout.json'
        with open(pinConfigFilePath, 'r') as f:
            pinConfigToBeLoaded = json.load(f)

        ir_pin = pinConfigToBeLoaded['ir_pin']
        led_pin = pinConfigToBeLoaded['led_pin']

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

        defaultstepperInner = {"minMove": 2000, "maxMove": 2500, "afterTrigger": 1360, "chanList": chanListInner}
        defaultstepperOuter = {"minMove": 2100, "maxMove": 2900, "afterTrigger": 1460, "chanList": chanListOuter}
        
        innerCircle = BoxCircle("innerCircle", boxState.cpuId)
        outerCircle = BoxCircle("outerCircle", boxState.cpuId)

        internetIsAvailable = True
        timestampInternetAvailable = time.time()
        internetCheckWaitWhileNotAvailable()
        
        googleHostForInternetCheck = "8.8.8.8"
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((googleHostForInternetCheck, 0))
        boxState.ipAddress = s.getsockname()[0]
        boxState.hostname = socket.gethostname()
       
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(button_led_pin, GPIO.OUT)
        GPIO.setup(button_pushed_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(led_pin, GPIO.OUT)
        GPIO.output(led_pin, GPIO.LOW)
        GPIO.setup(ir_pin, GPIO.IN)
        arr1 = [1, 1, 0, 0]
        arr2 = [0, 1, 0, 0]
        arrOff = [0, 0, 0, 0]

        moveIsBeingDone = False
        irTriggered = False
        
        firebaseConnection = FirebaseConnection(str(boxState.cpuId), '/home/pi/config.json')
        firebase_stream = ""
        
        getFirebaseValuesAndSetDefaultsIfNeeded()
        firebaseConnection.setPing()
        # this has to be done after getting the stepper chanlist
        for pin in innerCircle.settings.stepper.chanList:
            GPIO.setup(pin, GPIO.OUT)
        for pin in outerCircle.settings.stepper.chanList:
            GPIO.setup(pin, GPIO.OUT)

        firebaseConnection.setFirebaseValue("commands", Commands().getDict())

        firebaseConnection.setFirebaseValue("cpuId", boxState.cpuId, "state")
        firebaseConnection.setFirebaseValue("cpuId", boxState.cpuId, "innerCircle","circles")
        firebaseConnection.setFirebaseValue("name", innerCircle.name, innerCircle.name,"circles")
        firebaseConnection.setFirebaseValue("cpuId", boxState.cpuId, "outerCircle","circles")
        firebaseConnection.setFirebaseValue("name", outerCircle.name, outerCircle.name,"circles")
        firebaseConnection.setFirebaseValue("ipAddress", boxState.ipAddress, "state")
        firebaseConnection.setFirebaseValue("hostname", boxState.hostname, "state")
        firebaseConnection.setFirebaseValue("version", boxState.version, "state")
        firebaseConnection.setFirebaseValue("wifiDetails", wifiDetails, "state")

        pingSeconds = firebaseConnection.getPingSeconds()
        
        latestVersionAvailable = firebaseConnection.getBoxLatestVersion()
        checkVersionAndUpdateIfNeeded()

        pingTimestampFromStream = time.time() # initialize with now
        logger.info("setting pingTimestampFromStream to " + str(round(pingTimestampFromStream)))
        resetFirebaseStreams()
        firebaseCallbackThread = threading.Thread(target=firebase_callback_thread, args=(1,))
        firebaseCallbackThread.start()

        buttonThread = threading.Thread(target=thread_button, args=(1,))
        buttonThread.start()
        irThread = threading.Thread(target=thread_ir_sensor, args=(1,))
        irThread.start()
        timeThread = threading.Thread(target=thread_ping, args=(1,))
        timeThread.start()
        moveThreadInner = threading.Thread(target=thread_move_inner, args=(1,))
        moveThreadInner.start()
        moveThreadOuter = threading.Thread(target=thread_move_outer, args=(1,))
        moveThreadOuter.start()
        releaseBothMotors()
        setButtonLed(True)
        logger.info("---------------------------------")
        logger.info("PodQ box started. Version [" + boxState.version + "] latest_version ["+ latestVersionAvailable + "] CPU serial [" + str(boxState.cpuId) + "]")
        logger.info("---------------------------------")
        while (True):
            time.sleep(10)

    except KeyboardInterrupt:  # If CTRL+C is pressed, exit cleanly:
        logger.info("Keyboard interrupt")
    except Exception as err:
        logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    finally:
        logger.info("cleaning up the GPIO and exiting")
        setButtonLed(False)
        exitapp = True
        GPIO.cleanup()
        firebase_stream.close()
        # give the threads time to shut down before removing GPIO
        time.sleep(1)
        logger.info("Shutdown complete ---------------------------------------------------")
    logger.info("Goodbye! ---------------------------------------------------")
