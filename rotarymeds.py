
import RPi.GPIO as GPIO
import datetime 
import time
import threading
import json
import os
import logging
import socket #used for hostname
import traceback
import subprocess

version = "1.0.8"

googleHostForInternetCheck = "8.8.8.8"

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR000000000"
 
    return cpuserial

cpuserial = getserial()


folderPath = '/home/pi/shared/'
os.makedirs(folderPath + "logs/", exist_ok=True)
logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(folderPath + "logs/rotarymeds.log"),
        logging.StreamHandler()
    ])


logging.info("Version is " + version)


logging.info("CPU serial is [" + cpuserial + "]")
configFileName = 'config.json'
configFilePath = folderPath + configFileName


    
logging.info("checking internet connectivity")

def haveInternet():
    try:
        output = subprocess.check_output("ping -c 1 {}".format(googleHostForInternetCheck), shell=True)

    except Exception:
        return False

    return True


while(not haveInternet()):
    logging.info("internet is not available, sleeping 1 second")
    time.sleep(1)
    
logging.info("have internet connectivity")


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

logging.info("Loading pyrebase")
import pyrebase
logging.info("pyrebase loaded")
firebase = pyrebase.initialize_app(config)
database = firebase.database()

def setFirebaseValue(settingname, newValue, doLogging):
    currentValue = database.child("rotary").child(cpuserial).child(settingname).get()
    if(currentValue.val() != newValue):
        database.child("rotary").child(cpuserial).child(settingname).set(newValue)
        if(doLogging):
            logging.info("updated [" + settingname + "] from [" +str(currentValue.val()) +"] to[" + str(newValue) + "]")

def loadFirebaseValue(settingname, defaultValue):
    settingValue = database.child("rotary").child(cpuserial).child(settingname).get()
    if settingValue.val() is None:
        setFirebaseValue(settingname, defaultValue, True)
    returnVal = database.child("rotary").child(cpuserial).child(settingname).get().val()
    logging.info(settingname + " value is " + str(returnVal))
    return returnVal


defaultMoveSetting = {"inner": {"minMove": 2000, "maxMove": 2500, "afterTrigger": 1360}, "outer": {"minMove": 2100, "maxMove": 2600, "afterTrigger": 1640}}
moveSettings = loadFirebaseValue('moveSettings', defaultMoveSetting)
maxMoveInner = moveSettings["inner"]["maxMove"]
maxMoveOuter = moveSettings["outer"]["maxMove"]
minMoveInner = moveSettings["inner"]["minMove"]
minMoveOuter = moveSettings["outer"]["minMove"]
moveAfterTriggerInner = moveSettings["inner"]["afterTrigger"]
moveAfterTriggerOuter = moveSettings["outer"]["afterTrigger"]

defaultSchedule = [{"day": ["everyday"],"hour":7,"minute":0}]
scheduleOuter = loadFirebaseValue('scheduleOuter', defaultSchedule)
scheduleInner = loadFirebaseValue('scheduleInner', defaultSchedule)

isInnerDayForEveryOther = loadFirebaseValue("isInnerDayForEveryOther", False)

GPIO.setmode(GPIO.BCM)

exitapp = False
        
buttonLedPin = 6  
GPIO.setup(buttonLedPin,GPIO.OUT)

buttonPin = 5
GPIO.setup(buttonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

whiteLedPin = 16
GPIO.setup(whiteLedPin,GPIO.OUT)
GPIO.output(whiteLedPin,GPIO.LOW)

irSensorPin = 4
GPIO.setup(irSensorPin, GPIO.IN) 

chan_list_stepper_inner = [17,27,22,23] # GPIO ports to use
chan_list_stepper_outer = [24,13,26,12] # GPIO ports to use
delay=.001 # delay between each sequence step
#initialize array for sequence shift
arr1 = [1,1,0,0]
arr2 = [0,1,0,0]
arrOff = [0,0,0,0]
    
for pin in chan_list_stepper_inner:
    GPIO.setup(pin,GPIO.OUT)
for pin in chan_list_stepper_outer:
    GPIO.setup(pin,GPIO.OUT)
    

def rotateStateInnerDayForEveryOther():
    global isInnerDayForEveryOther

    newValue = not isInnerDayForEveryOther
    isInnerDayForEveryOther = newValue
    setFirebaseValue("isInnerDayForEveryOther", newValue, True)
    
    logging.info("rotateState : isInnerDayForEveryOther is set to " + str(isInnerDayForEveryOther))
    
    
moveIsBeingDone = False   
def move_stepper_inner():
    global moveIsBeingDone
    while (moveIsBeingDone):
        logging.info("inner: waiting for other move to be done")
        time.sleep(1)
    moveIsBeingDone = True
    move("move_stepper_inner", chan_list_stepper_inner, moveAfterTriggerInner, minMoveInner, maxMoveInner)
    moveIsBeingDone = False
    
def move_stepper_outer():
    global moveIsBeingDone
    while (moveIsBeingDone):
        logging.info("outer: waiting for other move to be done" , moveIsBeingDone)
        time.sleep(1)
    moveIsBeingDone = True
    move("move_stepper_outer", chan_list_stepper_outer, moveAfterTriggerOuter, minMoveOuter, maxMoveOuter)
    moveIsBeingDone = False
    
def holdBothMotors():
    global arr1 # enables the edit of arr1 var inside a function
    arrOUT = arr1[1:]+arr1[:1] # rotates array values of 1 digi
    GPIO.output(chan_list_stepper_inner, arrOUT)
    GPIO.output(chan_list_stepper_outer, arrOUT)
    
def releaseBothMotors():
    global arrOff
    GPIO.output(chan_list_stepper_outer, arrOff)
    GPIO.output(chan_list_stepper_inner, arrOff)
    
# this is a todo part 
def initiateRotariesToStartingPosition():
    global arr1 # enables the edit of arr1 var inside a function
    global arr2 # enables the edit of arr2 var inside a function
    
    def oneStep(chan_list):
        global arr1 
        global arr2
        arrOUT = arr1[3:]+arr1[:3] # rotates array values of 1 digi
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(chan_list, arrOUT)
        time.sleep(delay)
        

    while GPIO.input(irSensorPin) == GPIO.LOW:
        logging.info("initiateRotaries: it's white")
    
        for x in range(100):
            if GPIO.input(irSensorPin) == GPIO.LOW:
                oneStep(chan_list_stepper_inner)
            else:
                for y in range(moveAfterTriggerInner):
                    oneStep(chan_list_stepper_inner)
                break
                    
            
        for x in range(100):
            if GPIO.input(irSensorPin) == GPIO.LOW:
                oneStep(chan_list_stepper_outer)
            else:
                for y in range(moveAfterTriggerOuter):
                    oneStep(chan_list_stepper_outer)
                break
                    
    logging.info("initiateRotaries: it's no longer white")

stopMoving = False
def move(rotaryName, chan_list, moveAfterTrigger, minimumMove, maximumMove):
    global stopMoving
    global arr1 # enables the edit of arr1 var inside a function
    global arr2 # enables the edit of arr2 var inside a function
    
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
        arrOUT = arr1[3:]+arr1[:3] # rotates array values of 1 digi
        #arrOUT = arr1[1:]+arr1[:1] # rotates array values of 1 digit counterclockwise
        arr1 = arr2
        arr2 = arrOUT
        GPIO.output(chan_list, arrOUT)
        time.sleep(delay)
        if stopMoving and stepsDoneWhenIRtrigger == 0:
            stepsDoneWhenIRtrigger = stepsDone
        return stepsDone + 1
        
    while stepsDone < minimumMove:
        stepsDone = oneStep(stepsDone)

    while stepsDone < stepsDoneWhenIRtrigger + moveAfterTrigger and stepsDone < maximumMove: 
        stepsDone = oneStep(stepsDone)
    
    while stopMoving == False and stepsDone < maximumMove:
        stepsDone = oneStep(stepsDone)
    
    
    logMessage = rotaryName + " totalStepsDone [" + str(stepsDone) + "] stopMoving [" + str(stopMoving) + "] stepsDoneWhenIRtrigger [" + str(stepsDoneWhenIRtrigger) + "] stepsDoneAfterIRtrigger [" + str(stepsDone - stepsDoneWhenIRtrigger) + "] minimumMove [" + str(minimumMove) + "] maximumMove [" + str(maximumMove) + "]"
    logging.info("move    : " + logMessage)
        
    database.child("rotary").child(cpuserial).child(rotaryName).set(logMessage)
        
    
    GPIO.output(chan_list, arrOff)
    
    setButtonLedOn(False)
    GPIO.output(whiteLedPin,GPIO.HIGH)
                
    releaseBothMotors()
    logging.info(" ")

buttonLedIsOn = True
def setButtonLedOn(setToOn):
    global buttonLedIsOn
    if(setToOn):
        logging.info("setButtonLedOn    : turning ON the buttonLed")
        buttonLedIsOn = True
        GPIO.output(buttonLedPin,GPIO.HIGH)
        setFirebaseValue("buttonLedOn", True, True)
        
    else:
        logging.info("setButtonLedOn    : turning OFF the buttonLed")
        buttonLedIsOn = False
        GPIO.output(buttonLedPin,GPIO.LOW)
        setFirebaseValue("buttonLedOn", False, True)
        
    
def getWeekday(datetime):
    if datetime.weekday() == 0:
        return "Monday"
    if datetime.weekday() == 1:
        return "Tuesday"
    if datetime.weekday() == 2:
        return  "Wednesday"
    if datetime.weekday() == 3:
        return  "Thursday"
    if datetime.weekday() == 4:
        return  "Friday"  
    if datetime.weekday() == 5:
        return  "Saturday"  
    if datetime.weekday() == 6:
        return  "Sunday"  
    
    return "unknownDay"
        
def getNextMoveInner():
    global scheduleInner

    todayWeekday = getWeekday(datetime.datetime.today())
    
    nextMove = 0
    for scheduledMove in scheduleInner:
        for dayInRecord in scheduledMove['day']:
            
            isTodayMoveDay = False
            if(dayInRecord == "everyOtherDay" and isInnerDayForEveryOther):
                isTodayMoveDay = True
            elif(dayInRecord == todayWeekday):
                isTodayMoveDay = True
            elif(dayInRecord == "everyday"):
                isTodayMoveDay = True
                
            if(isTodayMoveDay):
                moveDate = datetime.datetime.today()
                moveTime = datetime.time(scheduledMove['hour'], scheduledMove['minute'], 0)
                possibleNextMove = datetime.datetime.combine(moveDate,moveTime)
                if(possibleNextMove < datetime.datetime.now()):
                    break
                elif(nextMove == 0):
                    nextMove = possibleNextMove
                elif(possibleNextMove < nextMove):
                    nextMove = possibleNextMove
                    logging.info("getNextMoveInner    :  setting nextMove to " + str(nextMove))
                
    
    setFirebaseValue("nextMoveInner", str(nextMove).strip(), True)
    return nextMove
        
def getNextMoveOuter():
    global scheduleOuter

    todayWeekday = getWeekday(datetime.datetime.today())
    
    nextMove = 0
    for scheduledMove in scheduleOuter:
        for dayInRecord in scheduledMove['day']:
            
            isTodayMoveDay = False
            if(dayInRecord == "everyOtherDay" and isInnerDayForEveryOther == False):
                isTodayMoveDay = True
            elif(dayInRecord == todayWeekday):
                isTodayMoveDay = True
            elif(dayInRecord == "everyday"):
                isTodayMoveDay = True
                
            if(isTodayMoveDay):
                moveDate = datetime.datetime.today()
                moveTime = datetime.time(scheduledMove['hour'], scheduledMove['minute'], 0)
                possibleNextMove = datetime.datetime.combine(moveDate,moveTime)
                if(possibleNextMove < datetime.datetime.now()):
                    break
                elif(nextMove == 0):
                    nextMove = possibleNextMove
                elif(possibleNextMove < nextMove):
                    nextMove = possibleNextMove
                    logging.info("getNextMoveOuter    :  setting nextMove to " + str(nextMove))
                    
    setFirebaseValue("nextMoveOuter", str(nextMove).strip(), True)
    return nextMove
        
        
def stream_handler(message):
    try:
        if message["path"] == "/scheduleInner":
            newVal = database.child("rotary").child(cpuserial).child("scheduleInner").get().val()
            logging.info("firebase: scheduleInner has new value: " + str(newVal))
        if message["path"] == "/scheduleOuter":
            newVal = database.child("rotary").child(cpuserial).child("scheduleOuter").get().val()
            logging.info("firebase: scheduleOuter has new value: " + str(newVal))
        if message["path"] == "/buttonLedOn":
            newVal = database.child("rotary").child(cpuserial).child("buttonLedOn").get().val()
            logging.info("firebase: buttonLedOn has new value: " + str(newVal))
    except Exception:
        logging.error("exception in stream_handler " +  traceback.format_exc())
     

# turn off led at midnight
def thread_time(name):
    lastTimeStampUpdate = 0    

    while not exitapp:
        try:
            time.sleep(1)
            now = datetime.datetime.now()
            timestampNow = time.time()
            if(timestampNow - lastTimeStampUpdate > 60):
                setFirebaseValue("timestamp", now.strftime('%Y-%m-%d %H:%M:%S'), True)
                lastTimeStampUpdate = timestampNow
            
            if(now.hour == 23 and now.minute == 59):
                logging.info("thread_time    : Nightly job before midnight")
                
                setButtonLedOn(False)
                
                rotateStateInnerDayForEveryOther()
                logging.info("thread_time    :have rotateStateInnerDayForEveryOther")
                time.sleep(70)
                logging.info("thread_time    : done sleeping")
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
    logging.info("thread_time    : exiting")    



def thread_move_inner(name):
    lastMove = datetime.datetime.now() + datetime.timedelta(days=-1)
    
    while not exitapp:
        try:
            nextMove = getNextMoveInner()
            if(nextMove != 0):            
                now = datetime.datetime.now()
                
                secondsBetween = abs((now-nextMove).total_seconds())
                
                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info("thread_move_inner    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20 ):
                        logging.info("thread_move_inner    :  it's time to move!")
                        lastMove = now
                        move_stepper_inner()
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
        time.sleep(3)
        
    logging.info("thread_move_inner    :   exiting")   


def thread_move_outer(name):
    lastMove = datetime.datetime.now() + datetime.timedelta(days=-1)
    
    while not exitapp:
        try:
            nextMove = getNextMoveOuter()
            if(nextMove != 0):            
                now = datetime.datetime.now()
                
                secondsBetween = abs((now-nextMove).total_seconds())
                
                if(abs((now-lastMove).total_seconds()) < 60):
                    logging.info("thread_move_outer    :  moved in the last minute, ignoring")
                else:
                    if(secondsBetween < 20 ):
                        logging.info("thread_move_outer    :  it's time to move!")
                        lastMove = now
                        move_stepper_outer()
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
        time.sleep(3)
        
    logging.info("thread_move_outer    :   exiting")   
        
def thread_button(name):

    timeButtonPressMostRecent = 0
    timeButtonPressSecondMostRecent = 0
    timeButtonNotPressed = 0
    timeGreenButtonPushed = 0
    
    global buttonLedIsOn
    while not exitapp: 
        try:
            
            if GPIO.input(buttonPin) == GPIO.HIGH :
                timestampNow = time.time()
                
                if(timeButtonNotPressed > timeButtonPressMostRecent):
                    logging.info("thread_button    : buttonPin button was pushed!")
                    GPIO.output(whiteLedPin,GPIO.LOW)
                    
                    if(buttonLedIsOn):
                        setButtonLedOn(False)
                    else:
                        setButtonLedOn(True)
                    
                    # new press
                    timeButtonPressSecondMostRecent = timeButtonPressMostRecent
                    timeButtonPressMostRecent = timestampNow
                    
                    if  timeButtonPressMostRecent - timeButtonPressSecondMostRecent < 1: # within one second
                        logging.info("thread_button    : button pressed two times, move!")
                        move_stepper_inner()
                        move_stepper_outer()
                

                        
            else:
                timeButtonNotPressed = time.time()
            time.sleep(delay)
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
        
    logging.info("thread_button    : exiting")
    
def thread_ir_sensor(name):
    timeIRtrigger = 0
    global stopMoving
    
    lastBlack = 0
    lastWhite = 0

    while not exitapp: 
        try: 
            if GPIO.input(irSensorPin) == GPIO.LOW:
                lastWhite = time.time()
            else : 
                lastBlack = time.time()

            if(lastWhite > lastBlack and lastWhite - lastBlack < 0.05 and stopMoving == False) : # just turned white
                stopMoving = True
                logging.info("thread_ir_sensor    : stopMoving")
            time.sleep(delay)
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
    logging.info("thread_ir_sensor    : exiting")    
    
     
if __name__=='__main__':
   
    try:
        timestampNow = time.time()
        timeGreenButtonPushed = timestampNow + 5
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect((googleHostForInternetCheck, 0))
        ipaddr = s.getsockname()[0]
        host = socket.gethostname()
        setFirebaseValue("ip-address", ipaddr, True)
        setFirebaseValue("hostname", host, True)
        setFirebaseValue("version", version, True)

        logging.info("next move today of inner is " + str(getNextMoveInner()))
        logging.info("next move today of outer is " + str(getNextMoveOuter()))
        
        buttonThread = threading.Thread(target=thread_button, args=(1,))
        buttonThread.start()
        logging.info("Main    : thread_button started")
        
        irThread = threading.Thread(target=thread_ir_sensor, args=(1,))
        irThread.start()
        logging.info("Main    : thread_ir_sensor started")
        
        timeThread = threading.Thread(target=thread_time, args=(1,))
        timeThread.start()
        logging.info("Main    : time thread stared")
        
        my_stream = database.child("rotary").child(cpuserial).stream(stream_handler)

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
    
    
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        logging.info("Keyboard interrupt")
    
    except Exception:
        logging.error("exception " +  traceback.format_exc())


        
    finally:
        logging.info("Main    : cleaning up the GPIO and exiting")
        setButtonLedOn(False)
        exitapp = True
        GPIO.cleanup()
        my_stream.close()
        time.sleep(1) # give the threads time to shut down before removing GPIO
        logging.info("Main    : Shutdown complete")
        
    
    logging.info("Main    : Goodbye!")
