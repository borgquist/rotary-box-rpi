import datetime
from datetime import timedelta
import pytz

class DateTimeFunctions:

    fmt = '%Y-%m-%d %H:%M:%S %Z%z'
    
    @staticmethod
    def getUtcNowIsoFormat():
        utc_now = pytz.utc.localize(datetime.datetime.utcnow())
        return utc_now.isoformat()

    @staticmethod
    def getDateTimeNowNormalized(timezone: str) -> datetime.datetime:
        pytzTimezone = pytz.timezone(timezone)
        return pytzTimezone.normalize(datetime.datetime.now().astimezone(pytzTimezone))

        
    @staticmethod
    def getDateTimeNormalized(datetimeValue: datetime.datetime, timezone) -> datetime.datetime:
        pytzTimezone = pytz.timezone(timezone)
        return pytzTimezone.normalize(datetimeValue.astimezone(pytzTimezone))

    @staticmethod
    def getWeekday(theDateTime: datetime.datetime) -> str:
        return theDateTime.strftime("%A")


    @staticmethod
    def isTodayEvenDay():
        daysSinceEpoch = DateTimeFunctions.daysSinceEpoch()
        return daysSinceEpoch % 2 == 0
    
    @staticmethod
    def daysSinceEpoch():
        return (datetime.datetime.utcnow() - datetime.datetime(1970,1,1)).days

    @staticmethod
    def getMinutesFromNow(normalizedDateTime: datetime.datetime, timezone: str) -> float:
        now = DateTimeFunctions.getDateTimeNowNormalized(timezone)
        return(normalizedDateTime - now).total_seconds() / 60

    @staticmethod
    def getHoursFromNow(normalizedDateTime: datetime.datetime, timezone: str) -> float:
        now = DateTimeFunctions.getDateTimeNowNormalized(timezone)
        return(normalizedDateTime - now).total_seconds() / (60*60)

    @staticmethod
    def getNormalizedDateTime(year: int, month: int, day: int, hour: int, minute: int, timezone: str) -> datetime.datetime:
        comparisonDateTime = pytz.timezone(timezone).localize(datetime.datetime(year, month, day, hour, minute))
        return comparisonDateTime

    @staticmethod
    def getTodayNormalizedDateTime(hour: int, minute: int, timezone: str) -> datetime.datetime:
        todaysDateNormalized = DateTimeFunctions.getDateTimeNowNormalized(timezone)
        
        year = todaysDateNormalized.year
        month= todaysDateNormalized.month
        day = todaysDateNormalized.day
        return DateTimeFunctions.getNormalizedDateTime(year, month, day, hour, minute, timezone)

    @staticmethod
    def isTimeBeforeNowWithTimezone(hour: int, minute: int, timezone: str) -> bool:
        todaysDateNormalized = DateTimeFunctions.getDateTimeNowNormalized(timezone)
        comparisonDateTime = DateTimeFunctions.getTodayNormalizedDateTime(hour, minute, timezone)

        if(comparisonDateTime < todaysDateNormalized):
            return True
        else:
            return False
    
    @staticmethod
    def getDateTimeFromScheduleWithTimezone(weekdayOfMove: str, hourOfMove: int, minuteOfMove: int, timezone: str) -> datetime.datetime:
        weekdayOfMove = weekdayOfMove.lower()

        candidateForNextMove = DateTimeFunctions.getTodayNormalizedDateTime(hourOfMove, minuteOfMove, timezone)
        isBeforeNow = DateTimeFunctions.isTimeBeforeNowWithTimezone(hourOfMove, minuteOfMove, timezone)

        if(weekdayOfMove == "everyday"):
            if(isBeforeNow):
                candidateForNextMove = candidateForNextMove + timedelta(days=1)
            return candidateForNextMove

        if(weekdayOfMove == "evendays"):
            if(DateTimeFunctions.isTodayEvenDay()):
                if(isBeforeNow):
                    candidateForNextMove = candidateForNextMove + timedelta(days=2)
            else:
                candidateForNextMove = candidateForNextMove + timedelta(days=1)
            return candidateForNextMove

        if(weekdayOfMove == "odddays"):
            if (not DateTimeFunctions.isTodayEvenDay()):
                if(isBeforeNow):
                    candidateForNextMove = candidateForNextMove + timedelta(days=2)
            else:
                candidateForNextMove = candidateForNextMove + timedelta(days=1)
            return candidateForNextMove

        todayNormalizedWeekday = DateTimeFunctions.getWeekday(candidateForNextMove).lower()
        if(weekdayOfMove == todayNormalizedWeekday and not isBeforeNow):
            return candidateForNextMove

        #it's a weekday and if today then it's already passed, count days until that weekday
        for x in range(7):
            candidateForNextMove = candidateForNextMove + timedelta(1)
            if(weekdayOfMove == DateTimeFunctions.getWeekday(candidateForNextMove).lower()):
                return candidateForNextMove
            
        print("could'nt find next")
        return None

    