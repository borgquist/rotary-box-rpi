from boxcirclesettings import BoxCircleSettings
from boxcirclestate import BoxCircleState

class BoxCircle:
    def __init__(self, name, cpuId):
        self.name = name
        self.cpuId = cpuId
        self.settings = BoxCircleSettings()
        self.state = BoxCircleState()

    def getDict(self):
        return self.__dict__

    def __str__(self):
        return str(self.__dict__)
