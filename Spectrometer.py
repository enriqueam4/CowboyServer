import clr
import sys
import os
import numpy as np
import logging
import time
import glob

clr.AddReference("System")
from System.IO import *
from System import String
from System.Collections.Generic import List
from System.Threading import AutoResetEvent
from ctypes import *

# Add needed dll references
sys.path.append(os.environ['LIGHTFIELD_ROOT'])
sys.path.append(os.environ['LIGHTFIELD_ROOT'] + "\\AddInViews")
clr.AddReference('PrincetonInstruments.LightFieldViewV5')
clr.AddReference('PrincetonInstruments.LightField.AutomationV5')
clr.AddReference('PrincetonInstruments.LightFieldAddInSupportServices')

# PI imports 
from PrincetonInstruments.LightField.Automation import Automation
from PrincetonInstruments.LightField.AddIns import ExperimentSettings
from PrincetonInstruments.LightField.AddIns import DeviceType
from PrincetonInstruments.LightField.AddIns import CameraSettings
from PrincetonInstruments.LightField.AddIns import SpectrometerSettings

logger = logging.getLogger(__name__)


class Operations:

    # INITIALIZATION
    def __init__(self):
        logger.debug('Here we go')
        self.auto = Automation(True, List[String]())
        self.application = self.auto.LightFieldApplication
        self.experiment = self.application.Experiment
        self.file_manager = self.application.FileManager
        self.acquireCompleted = AutoResetEvent(False)
        self.dataset = Dataset()
        time.sleep(3)
        logger.debug('Loaded')

    # ACQUISITION
    def acquire(self, *args):
        logger.debug('Called acquire directly! Args: ' + str(args))
        if self.device_found():
            self.experiment.ExperimentCompleted += self.experiment_completed
            try:
                self.experiment.Acquire()
                self.acquireCompleted.WaitOne()
            finally:
                self.experiment.ExperimentCompleted -= self.experiment_completed

            directory = self.experiment.GetValue(ExperimentSettings.FileNameGenerationDirectory)
            self.open_saved_image(directory)
            self.open_calib(directory)

            for file in os.listdir(directory):  # this is an absolute shit patch to the mem error
                if os.path.splitext(file)[1] == '.spe':
                    os.remove(os.path.join(directory, file))

        # print(self.dataset.x)
        # print(self.dataset.y)

        size = len(self.dataset.x)
        datapack = np.zeros((2, size))
        for i in range(size):
            datapack[0][i] = float(self.dataset.x[i])
            datapack[1][i] = float(self.dataset.y[i])

        return datapack.tolist()

    def acquire2(self, *args):
        logger.debug('Called acquire directly! Args: ' + str(args))
        if self.device_found():
            self.experiment.ExperimentCompleted += self.experiment_completed
            try:
                self.experiment.Acquire()
                self.acquireCompleted.WaitOne()
            finally:
                self.experiment.ExperimentCompleted -= self.experiment_completed

            directory = self.experiment.GetValue(ExperimentSettings.FileNameGenerationDirectory)
            self.open_saved_image(directory)
        print(self.dataset.x)
        size = len(self.dataset.x)
        datapack = np.zeros(size)
        for i in range(size):
            datapack[i] = self.dataset.x[i]
        return datapack.tolist()

    def calibrate2(self, *args):
        logger.debug('Called calibrate2 directly! Args: ' + str(args))
        if self.device_found():
            self.experiment.ExperimentCompleted += self.experiment_completed
            try:
                self.experiment.Acquire()
                self.acquireCompleted.WaitOne()
            finally:
                self.experiment.ExperimentCompleted -= self.experiment_completed

            directory = self.experiment.GetValue(ExperimentSettings.FileNameGenerationDirectory)
            self.open_calib(directory)
        print(self.dataset.y)
        size = len(self.dataset.y)
        datapack = np.zeros(size)
        for i in range(size):
            datapack[i] = self.dataset.y[i]
        return datapack.tolist()

    def abort(self, *args):
        logger.debug('Called abort directly! Args: ' + str(args))
        if self.device_found():
            self.experiment.Abort()

    # DATA MANAGEMENT
    def open_saved_image(self, directory):
        # Access previously saved image
        if os.path.exists(directory):
            print("\nOpening .spe file...")
            # Returns all .spe files
            files = glob.glob(directory + '/*.spe')
            # Returns recently acquired .spe file
            last_image_acquired = max(files, key=os.path.getctime)

            try:
                # Open file
                # TROUBLE IS HERE   V
                file_name = self.file_manager.OpenFile(
                    last_image_acquired, FileAccess.Read)
                # Access image
                self.get_image_data(file_name)
                file_name.Dispose()
            except IOError as e:
                print("Error: can not find file or read data")

        else:
            print(".spe file not found...")

    def move_spe(self, *args):
        home_directory = r'C:\Users\PHOTNCS03.LAB\Documents\LightField'
        new_directory = r'C:\Users\PHOTNCS03.LAB\Desktop\LIGHTFIELD SCANS'
        for filename in os.listdir(home_directory):
            if os.path.splitext(filename)[1] == '.spe':
                print('Moving: ' + filename)
                os.rename(os.path.join(home_directory, filename), os.path.join(new_directory, filename))

    def open_calib(self, directory):
        if os.path.exists(directory):
            print("\nOpening calibration file...")
            files = glob.glob(directory + '/*.spe')
            last_image_acquired = max(files, key=os.path.getctime)
            try:
                self.get_calib(last_image_acquired)
            except IOError:
                print("Error: can not find file or read data")
        else:
            print(".spe file not found...")

    def get_image_data(self, file):
        # Get the first frame
        image_data = file.GetFrame(0, 0)
        buffer = image_data.GetData()
        # SHOULD FIND CORRESPONDING METHODS FOR IMG_DATA
        self.dataset.x = np.zeros(len(buffer))
        for i in range(len(buffer)):
            self.dataset.x[i] = buffer[i]
        self.dataset.x.tolist()         # list necessary for json sterilization

    def get_calib(self, directory):
        file = open(directory, 'r', errors='ignore')
        stringy = file.read()
        stringy2 = stringy.split('<Wavelength xml:space="preserve">')[1]
        stringy3 = stringy2.split('</Wavelength>')[0]
        str_wavelength = stringy3.split(',')
        self.dataset.y = np.zeros(len(str_wavelength))
        for i in range(len(str_wavelength)):
            self.dataset.y[i] = float(str_wavelength[i])
        self.dataset.y.tolist()

    def experiment_completed(self, sender, event_args):
        print("Experiment Completed")
        self.acquireCompleted.Set()

    def device_found(self):
        # Find connected device
        for device in self.experiment.ExperimentDevices:
            if device.Type == DeviceType.Camera:
                return True

        # If connected device is not a camera inform the user
        print("Camera not found. Please add a camera and try again.")
        return False

    # SETTING VALUES

    def set_value(self, setting, value):
        if self.experiment.Exists(setting):
            if type(value[0][0]) == int:
                self.experiment.SetValue(setting, value[0][0])
            else:
                return

    def set_exposure_time(self, *args):
        logger.debug('Called set_exposure_time directly! Args: ' + str(args))
        self.set_value(CameraSettings.ShutterTimingExposureTime, args)
        return "Function Completed"

    def set_center_wavelength(self, *args):
        logger.debug('Called set_center_wavelength directly! Args: ' + str(args))
        self.set_value(SpectrometerSettings.GratingCenterWavelength, args)
        return "Function Completed"

    # GETTING VALUES
    def get_spectrometer_info(self, *args):
        logger.debug('Called get_spectrometer_info directly! Args: ' + str(args))
        print(String.Format("{0} {1}", "Center Wave Length:",
                            str(self.experiment.GetValue(SpectrometerSettings.GratingCenterWavelength))))
        print(String.Format("{0} {1}", "Grating:", str(self.experiment.GetValue(SpectrometerSettings.Grating))))
        return "Function Completed"

    def get_value(self, setting):
        return self.experiment.GetValue(setting)

    def get_grating(self, *args):
        logger.debug('Called get_grating directly! Args: ' + str(args))
        return self.get_value(SpectrometerSettings.GratingSelected)

    def get_center_wavelength(self, *args):
        logger.debug('Called get_center_wavelength directly! Args: ' + str(args))
        return self.get_value(SpectrometerSettings.GratingCenterWavelength)

    def get_exposure_time(self, *args):
        logger.debug('Called get_exposure_time directly! Args: ' + str(args))
        return self.get_value(CameraSettings.ShutterTimingExposureTime)

    def all_methods(self, cls):
        method_list = [func for func in dir(cls) if callable(getattr(cls, func))]
        return method_list


class Dataset:
    def __init__(self):
        self.x = []
        self.y = []


def main():
    s = Operations()
    bro = s.set_exposure_time([1000])  # 10 s
    s.move_spe()
    print(bro)


if __name__ == "__main__":
    main()
