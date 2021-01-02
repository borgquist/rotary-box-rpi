import RPi.GPIO as GPIO
import time
import logging
import threading
import os
import traceback
import subprocess


folderPath = '/home/pi/shared/'
os.makedirs(folderPath + "logs/", exist_ok=True)
logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
    datefmt='%Y-%m-%d:%H:%M:%S',
    level=logging.INFO,
    handlers=[
        logging.FileHandler(folderPath + "logs/resetbutton.log"),
        logging.StreamHandler()
    ])



GPIO.setmode(GPIO.BCM)

exitapp = False
delay=.001
resetButtonPin = 5
GPIO.setup(resetButtonPin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 

buttonLedPin = 6  
GPIO.setup(buttonLedPin,GPIO.OUT)

def flashButtonLed(speedInSeconds, nrFlashes, finalValue):
    ledOn = False
    for x in range(int(nrFlashes)):
        ledOn = not ledOn
        setButtonLedOn(ledOn)
        time.sleep(speedInSeconds)
    setButtonLedOn(finalValue)

def triggerResetMode():
    logging.info("reset wifi triggered")
    flashButtonLed(0.5, 6, True)
    
    os.system('sudo wifi-connect -s RotaryMeds-setupWiFi')
    logging.info("reset wifi complete")
    
    flashButtonLed(0.5, 10, False)
    logging.info("calling reboot")
    
    os.system('sudo reboot now')


 
googleHostForInternetCheck = "8.8.8.8"

def haveInternet():
    try:
        output = subprocess.check_output("ping -c 5 {}".format(googleHostForInternetCheck), shell=True)

    except Exception:
        return False

    return True



def thread_internet_connectivity(name):
    timestampInternetOK = 1
    timestampLastInternetNotOk = 0
    internetOutCount = 0
    while not exitapp: 
        try: 
            
            if(not haveInternet()):
                if(timestampLastInternetNotOk < timestampInternetOK):
                    internetOutCount = internetOutCount + 1
                    logging.warning("internet is not available, outage count: " + str(internetOutCount))
                    
                timestampLastInternetNotOk = time.time()
                flashButtonLed(0.3,10,False)
            else:
                if(timestampInternetOK < timestampLastInternetNotOk):
                    logging.info("there is internet again, outage count: " + str(internetOutCount))
                timestampInternetOK = time.time()
            time.sleep(5)
    
        except Exception as err:
            logging.error("exception " +  traceback.format_exc())
        
    logging.info("thread_internet_connectivity    : exiting")    

buttonLedIsOn = True
def setButtonLedOn(setToOn):
    global buttonLedIsOn
    if(setToOn):
        buttonLedIsOn = True
        GPIO.output(buttonLedPin,GPIO.HIGH)
    else:
        buttonLedIsOn = False
        GPIO.output(buttonLedPin,GPIO.LOW)
        
try:
    timestampNow = time.time()
    timeGreenButtonPushed = timestampNow + 5
    timeButtonNotPressed = 0
    timeButtonPressMostRecent = 0
    GPIO.setwarnings(False)
    fiveSecondPressDone = False
    pressCount = 0

    internetThread = threading.Thread(target=thread_internet_connectivity, args=(1,))
    internetThread.start()
    logging.info("thread_internet_connectivity stared")

    logging.info("ready")
    while (True): 

        if GPIO.input(resetButtonPin) == GPIO.HIGH :
            timestampNow = time.time()

            if(timeButtonNotPressed > timeButtonPressMostRecent):
                pressCount = pressCount + 1
                logging.info("button was pressed " + str(pressCount))

            timeButtonPressMostRecent = timestampNow
            
            if(timestampNow - timeButtonNotPressed > 3):
                if(fiveSecondPressDone == False):
                    logging.info("five second press, calling wifi-connect")
                    triggerResetMode()
                fiveSecondPressDone = True
            else:
                fiveSecondPressDone = False
        else:
            timeButtonNotPressed = time.time()

        time.sleep(delay)


except KeyboardInterrupt: # If CTRL+C is pressed, exit cleanly:
    logging.info("Keyboard interrupt")

except Exception:
    logging.error("exception " +  traceback.format_exc())
    
finally:
    logging.info("leaning up the GPIO and exiting")
    exitapp = True
    GPIO.cleanup()
    

logging.info("Goodbye!")
