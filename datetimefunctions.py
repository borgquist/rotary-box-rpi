import datetime
from datetime import timedelta
import logging


class DateTimeFunctions:

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
    def isTodayEvenDay():
        logging.info("calling isTodayEvenDay")
        daysSinceEpoch = DateTimeFunctions.daysSinceEpoch()
        logging.info("days since Epoch [" + daysSinceEpoch + "]")
        return daysSinceEpoch % 2 == 0

    
    @staticmethod
    def daysSinceEpoch():
        logging.info("calling daysSinceEpoch")
        today = datetime.datetime.today()
        past_date = datetime.date(1970, 1, 1) #Jan 1 1970
        return ((today - past_date).days)

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
        weekdayOfMove = weekdayOfMove.lower()
        candidateForNextMove = None
        timePart = datetime.time(hourOfMove, minuteOfMove, 0)
        todayWeekday = DateTimeFunctions.getWeekday(datetime.datetime.today()).lower()

        if(weekdayOfMove == "everyday"):
            if(DateTimeFunctions.isTimeBeforeNow(hourOfMove, minuteOfMove)):
                dayPart = datetime.datetime.today() + timedelta(days=1)
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            else:
                dayPart = datetime.datetime.today()
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            return candidateForNextMove

        if(weekdayOfMove == "evendays"):
            logging.info("checking evenDays")
        
            if(DateTimeFunctions.isTodayEvenDay()):
                logging.info("isTodayEvenDay is true")
                if(DateTimeFunctions.isTimeBeforeNow(hourOfMove, minuteOfMove)):
                    dayPart = datetime.datetime.today() + timedelta(days=2)
                    candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
                else:
                    dayPart = datetime.datetime.today()
                    candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            else:
                dayPart = datetime.datetime.today() + timedelta(days=1)
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            return candidateForNextMove

        if(weekdayOfMove == "odddays"):
            logging.info("checking oddDays")
            if(not DateTimeFunctions.isTodayEvenDay()):
                logging.info("isTodayEvenDay is NOT true")
                if(DateTimeFunctions.isTimeBeforeNow(hourOfMove, minuteOfMove)):
                    dayPart = datetime.datetime.today() + timedelta(days=2)
                    candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
                else:
                    dayPart = datetime.datetime.today()
                    candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            else:
                dayPart = datetime.datetime.today() + timedelta(days=1)
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            return candidateForNextMove

        if(weekdayOfMove == todayWeekday and not DateTimeFunctions.isTimeBeforeNow(hourOfMove, minuteOfMove)):
            dayPart = datetime.datetime.today()
            candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
            return candidateForNextMove

        #it's a weekday and if today then it's already passed, count days until that weekday
        for x in range(7):
            dayPart = datetime.datetime.today() + timedelta(days=x+1)
            if(DateTimeFunctions.getWeekday(dayPart).lower() == weekdayOfMove):
                candidateForNextMove = datetime.datetime.combine(dayPart, timePart)
                return candidateForNextMove
        
        return None