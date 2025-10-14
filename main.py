import firebase_admin

import Comms.bluetooth
from Comms.bluetooth.ble_sensor_lib import BLESensorManager
import Comms.wifi
from Comms.wifi.server import cred
import Comms.lora
from Comms.lora import lora
import sensor
from sensor.DFRobot_BloodOxygen_S import DFRobot_BloodOxygen_S_i2c
import time

class HeartRateMonitor:
    def __init__(self):
        # Initialize sensor (I2C bus 1, address 0x57)
        self.sensor = DFRobot_BloodOxygen_S_i2c(1, 0x57)

        if not self.sensor.begin():
            print("Sensor not found! Check wiring.")
            exit(1)

        self.sensor.sensor_start_collect()
        print("Sensor started collecting data...")

    def get_readings(self):
        """Get heart rate and SpO2 readings"""
        self.sensor.get_heartbeat_SPO2()
        return {
            'heart_rate': self.sensor.heartbeat,
            'spo2': self.sensor.SPO2
        }

    def get_temperature(self):
        """Get temperature reading"""
        return self.sensor.get_temperature_c()


# Usage in your main program
if __name__ == "__main__":
    monitor = HeartRateMonitor()

    try:
        while True:
            if not firebase_admin._apps:
                firebase_admin.initialize_app(cred, {
                    "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"
                })

            readings = monitor.get_readings()
            temp = monitor.get_temperature()

            print(f"Heart Rate: {readings['heart_rate']} bpm")
            print(f"SpO2: {readings['spo2']}%")
            print(f"Temperature: {temp:.1f}°C")
            print("-" * 20)

            sensor = BLESensorManager("TestSensor")
            sensor.set_heart_rate(80)
            sensor.set_oxygen_level(97)
            status = sensor.get_status()
            print("Current status:", status)

            time.sleep(2)  # Read every 2 seconds


    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.sensor.sensor_end_collect()

