import json

class Stepper:
    name = "unknown"
    maxMove = 3000
    minMove = 2000
    afterTrigger = 1000
    chanList = []
    def __str__(self):
        return "maxMove [" + str(self.maxMove) + "] minMove [" + str(self.minMove) + "] afterTrigger [" + str(self.afterTrigger) + "]"

    def toJSON(self):
        return {"name": self.name,
                "maxMove": self.maxMove,
                "minMove": self.minMove,
                "afterTrigger": self.afterTrigger
                }
