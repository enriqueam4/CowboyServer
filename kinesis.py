"""" Uses Kinesis to control Thorlabs long travel stage in XYZ configuration
"""
import clr
import sys
import time
import numpy as np
from System import Decimal
from System.Collections import *

# constants
sys.path.append(r"C:\Program Files\Thorlabs\Kinesis")

# add .net reference and import so python can see .net
clr.AddReference("Thorlabs.MotionControl.Controls")
import Thorlabs.MotionControl.Controls

print(Thorlabs.MotionControl.Controls.__doc__)

# Add references so Python can see .Net
clr.AddReference("Thorlabs.MotionControl.DeviceManagerCLI")
clr.AddReference("Thorlabs.MotionControl.GenericMotorCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoUI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServoCLI")
clr.AddReference("Thorlabs.MotionControl.KCube.DCServo")

from Thorlabs.MotionControl.DeviceManagerCLI import *
from Thorlabs.MotionControl.GenericMotorCLI import *
from Thorlabs.MotionControl.KCube.DCServoCLI import *
from Thorlabs.MotionControl.KCube.DCServoUI import *
from Thorlabs.MotionControl.GenericMotorCLI.ControlParameters import *
from Thorlabs.MotionControl.GenericMotorCLI.AdvancedMotor import *
from Thorlabs.MotionControl.GenericMotorCLI.KCubeMotor import *


class KCubeDCServo:

    def __init__(self, *args):
        DeviceBuild = DeviceManagerCLI.BuildDeviceList()
        serials = DeviceManagerCLI.GetDeviceList(27)
        serial = serials[0]
        print(serials)
        self.device = Thorlabs.MotionControl.KCube.DCServoCLI.KCubeDCServo.CreateKCubeDCServo(serial)
        self.device.Connect(serial)
        self.device.WaitForSettingsInitialized(5000)
        self.motorConfiguration = self.device.LoadMotorConfiguration(serial)
        self.motorConfiguration.UpdateCurrentConfiguration()
        self.currentDeviceSettings = self.device.MotorDeviceSettings
        self.device.SetSettings(self.currentDeviceSettings, True, False)
        self.deviceInfo = self.device.GetDeviceInfo()
        self.calibrationfile = self.device.GetCalibrationFile()
        self.device.EnableDevice()

    def move_to(self, position, *args):
        try:
            user_input = int(position)
        except ValueError:
            print("Please Enter a digit and not a " + str(type(position)))
            return
        else:
            print("Moving to position " + str(position)+" degrees.")
            self.device.MoveTo(Decimal(position), 60000)
            self.device.StopPolling()
            print("Final Position: " + str(self.device.Position))

    def home(self):
        self.device.Home(60000)

    def print_position(self, *args):
        print(self.device.Position)

    def return_position(self, *args):
        return Decimal.ToInt32(self.device.Position)


def main():
    device = KCubeDCServo()
    a = device.return_position()
    device.home()
    print("yeehaw")


if __name__ == "__main__":
    main()
