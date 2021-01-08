import datetime
from datetime import timedelta
import logging
import os





class DateTimeFunctions:
    folderPath = '/home/pi/shared/'
    os.makedirs(folderPath + "logs/", exist_ok=True)
    logging.basicConfig(format='%(asctime)s.%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%Y-%m-%d:%H:%M:%S',
                        level=logging.INFO,
                        handlers=[
                            logging.FileHandler(
                                folderPath + "logs/datetimefunctions.log"),
                            logging.StreamHandler()
                        ])
    logging.info("accessing datetimefunctions.py")

    @staticmethod
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
    @staticmethod
    def isTimeBeforeNow(hourOfMove, minuteOfMove):
            moveTime = datetime.time(hourOfMove, minuteOfMove, 0)
            todaysDate = datetime.datetime.today()
            possibleNextMove = datetime.datetime.combine(todaysDate, moveTime)
            if(possibleNextMove < datetime.datetime.now()):
                return True
            else:
                return False
    @staticmethod
    def dateTimeFromSchedule(weekdayOfMove, hourOfMove, minuteOfMove):
        candidateForNextMove = None
        timePart = datetime.time(hourOfMove, minuteOfMove, 0)
        todayWeekday = DateTimeFunctions.getWeekday(datetime.datetime.today())

        if(weekdayOfMove == "everyday"):
            if(DateTimeFunctions.isTimeBeforeNow(hourOfMove, minuteOfMove)):
                logging.info("has already passed today: [" + str(hourOfMove) + "] minute [" + minuteOfMove + "] is before now [" + str(datetime.datetime.now()) + "]")
                dayPart = datetime.datetime.today() + timedelta(days=1)
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            else:
                logging.info("this is for today and hasn't passed: [" + str(hourOfMove) + "] minute [" + minuteOfMove + "] is NOT before now [" + str(datetime.datetime.now()) + "]")
                dayPart = datetime.datetime.today()
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            logging.info("everyday identified candidate: " + candidateForNextMove.strftime('%Y-%m-%d %H:%M:%S'))
            return candidateForNextMove

        if(weekdayOfMove == todayWeekday and not self.isTimeBeforeNow(hourOfMove, minuteOfMove)):
            dayPart = datetime.datetime.today()
            candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            logging.info("nextDateTime identified candidate: " + candidateForNextMove.strftime('%Y-%m-%d %H:%M:%S'))
            return candidateForNextMove

        #it's a weekday and if today then it's already passed, count days until that weekday
        for x in range(5):
            dayPart = datetime.datetime.today() + timedelta(days=x+1)
            if(dayPart == weekdayOfMove):
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
                logging.info("identified candidate [" + str(x + 1) + "] days from now: " + candidateForNextMove.strftime('%Y-%m-%d %H:%M:%S'))
                return candidateForNextMove
        
        logging.warning("this shouldn't happen, we should have found it by now [" + weekdayOfMove + "] hour [" + hourOfMove + "] minute [" + minuteOfMove + "] now ["+ datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + "]" )
        return None