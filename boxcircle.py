from boxcirclesettings import BoxCircleSettings
from boxcirclestate import BoxCircleState

class BoxCircle:
    def __init__(self):
        self.settings = BoxCircleSettings()
        self.state = BoxCircleState()
    
    def __str__(self):
        return "settings [" + str(self.settings) + "] state [" + str(self.state) + "]"
