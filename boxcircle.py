from boxcirclesettings import BoxCircleSettings
from boxcirclestate import BoxCircleState

class BoxCircle:
    settings = BoxCircleSettings()
    state = BoxCircleState()
    
    def __str__(self):
        return "settings [" + str(self.settings) + "] state [" + str(self.state) + "]"
