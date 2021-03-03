from boxcirclesettings import BoxCircleSettings
from boxcirclestate import BoxCircleState

class BoxCircle:
    def __init__(self, name, cpuId):
        self.name = name
        self.cpuId = cpuId
        self.settings = BoxCircleSettings()
        self.state = BoxCircleState()
    
    def __str__(self):
        return "name [" + self.name + "] cpuId [" + self.cpuId +"] settings [" + str(self.settings) + "] state [" + str(self.state) + "]"
