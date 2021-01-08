from boxsettings import FirebaseBoxSettings
from boxstate import FirebaseBoxState

class Box:
    cpuId = "0.0.0"
    boxSettings = FirebaseBoxSettings
    boxState = FirebaseBoxState

    def __str__(self):
        return "cpuId [" + str(self.cpuId) + "] boxSettings [" + str(self.boxSettings) + "] boxState [" + str(self.boxState) + "]"
