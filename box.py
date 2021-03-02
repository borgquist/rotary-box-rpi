from boxcircle import BoxCircle
from boxstate import BoxState
from boxcircle import BoxCircle

class Box:
    cpuId = "0.0.0"
    boxState = BoxState()
    innerCircle = BoxCircle()
    outerCircle = BoxCircle()

    def __str__(self):
        return "cpuId [" + str(self.cpuId) + "] boxState [" + str(self.boxState) + "] innerCircle [" + str(self.innerCircle) + "] outerCircle [" + str(self.outerCircle) + "]"
