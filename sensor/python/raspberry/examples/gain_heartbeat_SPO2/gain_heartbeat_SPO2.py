# -*- coding: utf-8 -*
'''
  @file  gain_heartbeat_SPO2.py
  @n brief： Get heart rate and oxygen saturation
  @copyright   Copyright (c) 2010 DFRobot Co.Ltd (http://www.dfrobot.com)
  @license     The MIT License (MIT)
  @author      PengKaixing(kaixing.peng@dfrobot.com)
  @version     V1.0.0
  @date        2021-03-28
  @get         from https://www.dfrobot.com
  @url         https://github.com/DFRobot/DFRobot_BloodOxygen_S
'''

import sys
import os
import time
import RPi.GPIO as GPIO

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.realpath(__file__)))))
from DFRobot_BloodOxygen_S import *

'''
  ctype=1：UART
  ctype=0：IIC
'''
ctype=0

if ctype==0:
  I2C_1       = 0x01               # I2C_1 Use i2c1 interface (or i2c0 with configuring Raspberry Pi file) to drive sensor
  I2C_ADDRESS = 0x57               # I2C device address, which can be changed by changing A1 and A0, the default address is 0x77
  max30102 = DFRobot_BloodOxygen_S_i2c(I2C_1 ,I2C_ADDRESS)

def setup():
  while (False == max30102.begin()):
    print("init fail!")
    time.sleep(1)
  print("start measuring...")
  max30102.sensor_start_collect()
  time.sleep(1)
  
def loop():
    max30102.get_heartbeat_SPO2()
    if max30102.SPO2==-1:
        print("SPO2 : N/A")    
    else :
        print("SPO2 : "+str(max30102.SPO2)+"%")
    if max30102.heartbeat==-1:
        print("Heart rate : N/A")
    else :
        print("Heart rate : "+str(max30102.heartbeat)+"BPM")
    time.sleep(0.5)
    

if __name__ == "__main__":
  setup()
  while True:
    loop()
