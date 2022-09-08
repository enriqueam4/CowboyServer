# This code is used to communicate with hwserver
import pyvisa
from pymeasure.instruments.keithley import Keithley2400
from pymeasure.adapters import SerialAdapter
from ctypes import util
import time
import sys
import os
print("FILE PATH" + str(os.getcwd()))
sys.path.append(os.getcwd())
sys.path.insert(1, r'C:\Users\iHR 550\Documents\ModuleServer\mymodules\upyrttl')
import rtttl
import songs
print(util.find_library("visa"))
from ctypes import c_float
from time import sleep
import numpy as np

class Sourcemeter(Keithley2400):
    def __init__(self):
        #rm = pyvisa.ResourceManager()
        # ports = rm.list_resources()
        self.keithley = Keithley2400('COM6')
        self.keithley.reset()
        self.keithley.use_front_terminals()
        self.keithley.measure_current()
        sleep(0.1)
        self.keithley.enable_source()
        #self.list_songs()
        
        self.play_song("A-Team")


    def measure_current(self):
        return self.keithley.current

    def measure_voltage(self):
        return self.keithley.source_voltage

    def set_voltage(self, val): 
        self.keithley.source_voltage = val
        return self.keithley.source_voltage

    def IV_Curve(self,min_voltage, max_voltage, n_steps, wait):
        voltages = np.linspace(min_voltage,max_voltage,num=n_steps)
        currents = np.zeros_like(voltages)
        for i in range(n_steps):
            self.keithley.source_voltage = voltages[i]
            sleep(float(wait))
            currents[i] = self.keithley.current
        
        self.keithley.source_voltage = 0
        return currents.tolist()
        
    def play_note(self, freq, msec):
        # print('freq = {:6.1f} msec = {:6.1f}'.format(freq, msec/1000))
        if freq > 0:
            self.keithley.beep(freq, msec/1000)
        time.sleep(.85*msec/1000)
        time.sleep(.0005)

    def play_song(self, string):
        print(string)
        song = songs.find(string)
        tune = rtttl.RTTTL(song)
        for freq, msec in tune.notes():
            self.play_note(freq, msec)
        return string

    def list_songs(self):
        song_list = []
        for song in songs.SONGS:
            song_name = song.split(':')[0]
            song_list.append(song_name)
            print(song_name)
        return song_list


def main():
    print("Connecting to Keithley Sourcemeter")
    rm = pyvisa.ResourceManager()
    ports = rm.list_resources()
    print(ports)
    a = Sourcemeter()
    dilly = a.IV_Curve(0,10,9)
    print(dilly)


if __name__=="__main__":
    main()

# Oct 19,2021
# Updated February 23, 2022
