from stepper import Stepper

class BoxCircleSettings:
    def __init__(self):
        self.stepper = Stepper()
        self.schedules = []
        self.nrPockets = 0
    
    def getDict(self):
        return self.__dict__

    def __str__(self):
        return str(self.__dict__)
