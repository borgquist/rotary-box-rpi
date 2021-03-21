import RPi.GPIO as GPIO
import time
import logging
import threading
import os
import traceback
import subprocess
import json

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

def triggerResetMode():
    logger.info("reset wifi triggered")
    flashButtonLed(0.5, 6, True)
    
    os.system('sudo wifi-connect -s PodQ-setupWiFi')
    logger.info("reset wifi complete")
    
    flashButtonLed(0.5, 10, False)
    logger.info("calling reboot")
    
    os.system('sudo reboot now')

def haveInternet() -> bool:
    googleHostForInternetCheck = "8.8.8.8"
    try:
        output = subprocess.check_output(
            "ping -c 1 {}".format(googleHostForInternetCheck), shell=True)
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
                    logger.warning("internet is not available, outage count: " + str(internetOutCount))
                flashButtonLed(0.5, 6, True) #works as a sleep too
                timestampLastInternetNotOk = time.time()
            else:
                if(timestampInternetOK < timestampLastInternetNotOk):
                    logger.info("there is internet again, outage count: " + str(internetOutCount))
                timestampInternetOK = time.time()
                time.sleep(5)
    
        except Exception as err:
            logger.error("exception " +  traceback.format_exc())
        
    logger.info("thread_internet_connectivity    : exiting")    

def thread_button(name):
    timeButtonNotPressed = 0
    while not exitapp:
        try:
            if GPIO.input(button_pushed_pin) == GPIO.HIGH :
                if(time.time() - timeButtonNotPressed > 5):
                    if(fiveSecondPressDone == False):
                        logger.info("five second press, calling wifi-connect")
                        triggerResetMode()
                    fiveSecondPressDone = True
                else:
                    fiveSecondPressDone = False
            else:
                timeButtonNotPressed = time.time()

            time.sleep(1) #sleeping a second, doesn't matter that this is long since we are waiting for 5 seconds of press (6 makes no difference)
        except Exception as err:
            logging.error("exception " + str(err) + " trace: " + traceback.format_exc())

    logger.info("exiting")

if __name__ == '__main__':
    try:
        exitapp = False
        folderPath = '/home/pi/'
        os.makedirs(folderPath + "logs/", exist_ok=True)
        logFormat = '%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] [%(funcName)s] %(message)s'
        date_fmt = '%a %d %b %Y %H:%M:%S'
        logging.basicConfig(format=logFormat, datefmt=date_fmt, level=logging.INFO)
        logger = logging.getLogger('podq')
        logger.setLevel(logging.INFO)
        file_handler = logging.FileHandler(folderPath + "logs/wifi-connect-podq.log")
        file_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(logFormat, date_fmt)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        pinConfigFilePath = '/home/pi/pinlayout.json'
        with open(pinConfigFilePath, 'r') as f:
            pinConfigToBeLoaded = json.load(f)

        GPIO.setmode(GPIO.BCM)
        button_pushed_pin = pinConfigToBeLoaded['button_pushed_pin']
        GPIO.setup(button_pushed_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
        button_led_pin = pinConfigToBeLoaded['button_led_pin']
        GPIO.setup(button_led_pin,GPIO.OUT)

        timeButtonNotPressed = 0
        GPIO.setwarnings(False)
        fiveSecondPressDone = False
        
        buttonThread = threading.Thread(target=thread_button, args=(1,))
        buttonThread.start()
        logger.info("thread_button stared")

        internetThread = threading.Thread(target=thread_internet_connectivity, args=(1,))
        internetThread.start()
        logger.info("thread_internet_connectivity stared")
        logger.info("Podq wifi-connect monitor started")
        while (True):
            time.sleep(10)


    except KeyboardInterrupt:  # If CTRL+C is pressed, exit cleanly:
        logger.info("Keyboard interrupt")
    except Exception as err:
        logging.error("exception " + str(err) + " trace: " + traceback.format_exc())
    finally:
        logger.info("cleaning up the GPIO and exiting")
        exitapp = True
        GPIO.cleanup()
        time.sleep(1)
        logger.info("Shutdown complete")

    logger.info("Goodbye!")
