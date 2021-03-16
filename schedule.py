from utilityfunctions import UtilityFunctions

class Schedule:
    def __init__(self):
        self.id = UtilityFunctions.generateId()
        self.day = "everyday"
        self.hour = 7
        self.minute = 0
   
    def __str__(self):
        return "id, [" + str(self.id) + "],  day [" + str(self.day) + "] hour [" + str(self.hour) + "] minute [" + str(self.minute) + "]"
