from boxcirclesettings import BoxCircleSettings
from boxcirclestate import BoxCircleState

class BoxCircle:
    def __init__(self, name):
        self.name = name
        self.settings = BoxCircleSettings()
        self.state = BoxCircleState()
    
    def __str__(self):
        return "name [" + self.name + "] settings [" + str(self.settings) + "] state [" + str(self.state) + "]"
