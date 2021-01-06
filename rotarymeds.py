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

version = "1.0.17"

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

def setFirebaseValue(settingname, newValue):
    currentValue = database.child("box").child("boxes").child(cpuserial).child(settingname).get()
    if(currentValue.val() != newValue):
        database.child("box").child("boxes").child(cpuserial).child(settingname).set(newValue)
        logging.info("updated [" + settingname + "] from [" +str(currentValue.val()) +"] to[" + str(newValue) + "]")    
        

def getFirebaseValue(settingname, defaultValue):
    settingValue = database.child("box").child("boxes").child(cpuserial).child(settingname).get()
    if settingValue.val() is None:
        setFirebaseValue(settingname, defaultValue)
    returnVal = database.child("box").child("boxes").child(cpuserial).child(settingname).get().val()
    logging.info(settingname + " value is " + str(returnVal))
    return returnVal

def getLatestBoxVersionAvailable():
    latestVersion = database.child("box").child("latest_version").get()
    if latestVersion.val() is None:
        logging.warning("couldn't get latest_version")
        return "unknown"
    
    logging.info("latest_version is: " + str(latestVersion.val()))
    return str(latestVersion.val())


    
    
defaultStepSettings = {"inner": {"minMove": 2000, "maxMove": 2500, "afterTrigger": 1360}, "outer": {"minMove": 2100, "maxMove": 2600, "afterTrigger": 1640}}
stepSettings = getFirebaseValue('stepSettings', defaultStepSettings)
maxMoveInner = stepSettings["inner"]["maxMove"]
maxMoveOuter = stepSettings["outer"]["maxMove"]
minMoveInner = stepSettings["inner"]["minMove"]
minMoveOuter = stepSettings["outer"]["minMove"]
moveAfterTriggerInner = stepSettings["inner"]["afterTrigger"]
moveAfterTriggerOuter = stepSettings["outer"]["afterTrigger"]

defaultSchedule = {"inner":[{"day": ["everyday"],"hour":17,"minute":0}],"outer":[{"day": ["everyday"],"hour":18,"minute":0}]}
schedule = getFirebaseValue('schedule', defaultSchedule)

scheduleOuter = schedule["outer"]
scheduleInner = schedule["inner"]

def getLatestScheduleFromFirebase():
    global scheduleInner
    global scheduleOuter
    schedule = getFirebaseValue('schedule', defaultSchedule)
    scheduleOuter = schedule["outer"]
    scheduleInner = schedule["inner"]

setFirebaseValue("moveNowInner", False)
setFirebaseValue("moveNowOuter", False)
setFirebaseValue("setButtonLed", False)

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
    now = datetime.datetime.now()
    
    
    latestMove = {
        "totalStepsDone": stepsDone, 
        "stopMoving": stopMoving, 
        "stepsDoneWhenIRtrigger": stepsDoneWhenIRtrigger,
        "stepsDoneAfterIRtrigger": stepsDone - stepsDoneWhenIRtrigger,
        "minimumMove": minimumMove,
        "maximumMove": maximumMove,
        "timestamp": now.strftime('%Y-%m-%d %H:%M:%S'),
    }
    
    #TODO move to setting method at start
    database.child("box").child("boxes").child(cpuserial).child("latestMove").child(rotaryName).set(latestMove)
    
    GPIO.output(chan_list, arrOff)
    
    setButtonLedOn(True)
               
    releaseBothMotors()
    logging.info(" ")

buttonLedIsOn = True
def setButtonLedOn(setToOn):
    global buttonLedIsOn
    if(setToOn):
        logging.info("setButtonLedOn    : turning ON the buttonLed")
        buttonLedIsOn = True
        GPIO.output(buttonLedPin,GPIO.HIGH)
        GPIO.output(whiteLedPin,GPIO.HIGH)
        setFirebaseValue("buttonLedOn", True)
        
    else:
        logging.info("setButtonLedOn    : turning OFF the buttonLed")
        buttonLedIsOn = False
        GPIO.output(buttonLedPin,GPIO.LOW)
        GPIO.output(whiteLedPin,GPIO.LOW)
        setFirebaseValue("buttonLedOn", False)
    
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

#TODO these two methods call firebase too often, no need to keep checking if we know the value hasn't changed  
nextMoveInner = 0      
def getNextMoveInner():
    global scheduleInner
    global nextMoveInner

    todayWeekday = getWeekday(datetime.datetime.today())
    
    nextMove = 0
    for scheduledMove in scheduleInner:
        for dayInRecord in scheduledMove['day']:
            
            isTodayMoveDay = False

            if(dayInRecord == todayWeekday):
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
    if(str(nextMove) != str(nextMoveInner)):
        logging.info("nextMoveInner has changed, old [" + str(nextMoveInner) + "] new [" + str(nextMove) + "] updating Firebase" )
        setFirebaseValue("nextMoveInner", str(nextMove).strip())
        nextMoveInner = nextMove
    
    return nextMove
        
def getNextMoveOuter():
    global scheduleOuter

    todayWeekday = getWeekday(datetime.datetime.today())
    
    nextMove = 0
    for scheduledMove in scheduleOuter:
        for dayInRecord in scheduledMove['day']:
            
            isTodayMoveDay = False

            if(dayInRecord == todayWeekday):
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
                    
    setFirebaseValue("nextMoveOuter", str(nextMove).strip())
    return nextMove
        
        
#TODO there could be issues where these are set while the internet is down (as checked in thread_time), would miss an update if it is
def stream_handler(message):
    try:
        if message["path"].startswith("/schedule"):
            newVal = database.child("box").child("boxes").child(cpuserial).child("schedule").get().val()
            logging.info("firebase: schedule has new value: " + str(newVal))
            getLatestScheduleFromFirebase()
        if message["path"] == "/setButtonLed":
            newVal = database.child("box").child("boxes").child(cpuserial).child("setButtonLed").get().val()
            logging.info("firebase: setButtonLed has new value: " + str(newVal))
            if(newVal == "on"):
                setButtonLedOn(True)
            if(newVal == "off"):
                setButtonLedOn(False)
            setFirebaseValue("setButtonLed", False)
        if message["path"] == "/moveNowOuter":
            newVal = database.child("box").child("boxes").child(cpuserial).child("moveNowOuter").get().val()
            logging.info("firebase: moveNowOuter has new value: " + str(newVal))
            if(bool(newVal)):
                logging.info("we should move outer now, setting moveNowOuter to false before moving to avoid multiple triggers")
                setFirebaseValue("moveNowOuter", False)
                move_stepper_outer()
        if message["path"] == "/moveNowInner":
            newVal = database.child("box").child("boxes").child(cpuserial).child("moveNowInner").get().val()
            logging.info("firebase: moveNowInner has new value: " + str(newVal))
            if(bool(newVal)):
                logging.info("we should move outer now, setting moveNowInner to false before moving to avoid multiple triggers")
                setFirebaseValue("moveNowInner", False)
                move_stepper_inner()
    except Exception:
        logging.error("exception in stream_handler " +  traceback.format_exc())
     
# turn off led at midnight
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
                logging.info("internet is back, resetting the stream to firebase")
                setupStreamToFirebase()

            
            if(timestampNow - lastTimeStampUpdate > 60):
                setFirebaseValue("timestamp", now.strftime('%Y-%m-%d %H:%M:%S'))
                lastTimeStampUpdate = timestampNow
            

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
        
        time.sleep(5)
        
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
        
        time.sleep(5)
        
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
                    
                    if(buttonLedIsOn):
                        setButtonLedOn(False)
                    else:
                        setButtonLedOn(True)
                    
                    # new press
                    timeButtonPressSecondMostRecent = timeButtonPressMostRecent
                    timeButtonPressMostRecent = timestampNow
                    
                    if  timeButtonPressMostRecent - timeButtonPressSecondMostRecent < 2: # double click
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

my_stream = ""
def setupStreamToFirebase():
    global my_stream
    logging.info("setting up the stream to firebase")
    my_stream = database.child("box").child("boxes").child(cpuserial).stream(stream_handler)
    logging.info("done setting up the stream to firebase")
        
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
        setFirebaseValue("ipAddress", ipaddr)
        setFirebaseValue("hostname", host)
        setFirebaseValue("version", version)

        latestVersionAvailable = getLatestBoxVersionAvailable()
        if(version != latestVersionAvailable):
            if(latestVersionAvailable == "unknown"):
                logging.error("unable to get latest_version from firebase")
            else:
                logging.warning("our version [" + version + "] latest_version [" + latestVersionAvailable + "]")
        else:
            logging.info("OK our version [" + version + "] latest_version [" + latestVersionAvailable + "]")

        
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
    
    
    except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
        logging.info("Keyboard interrupt")
    
    except Exception:
        logging.error("exception " +  traceback.format_exc())


        
    finally:
        logging.info("Main    : cleaning up the GPIO and exiting")
        setButtonLedOn(False)
        exitapp = True
        GPIO.cleanup()
        logging
        my_stream.close()
        time.sleep(1) # give the threads time to shut down before removing GPIO
        logging.info("Main    : Shutdown complete")
        
    
    logging.info("Main    : Goodbye!")
