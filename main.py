import firebase_admin
import sys
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
        self.sensor = DFRobot_BloodOxygen_S_i2c(1, 0x57)
        self.initialized = False

        if self.sensor.begin():
            self.sensor.sensor_start_collect()
            self.initialized = True
            print("Sensor started successfully")

            # Register cleanup handlers
            atexit.register(self.cleanup)
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            print("Sensor initialization failed!")

    def cleanup(self):
        """Properly shutdown the sensor"""
        if self.initialized:
            print("Shutting down sensor...")
            self.sensor.sensor_end_collect()
            # Small delay to ensure command is processed
            time.sleep(0.5)
            self.initialized = False

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C and other termination signals"""
        print("\nReceived shutdown signal...")
        self.cleanup()
        sys.exit(0)

    def get_readings(self):
        if not self.initialized:
            return None

        self.sensor.get_heartbeat_SPO2()
        return {
            'heart_rate': self.sensor.heartbeat,
            'spo2': self.sensor.SPO2
        }

    def __del__(self):
        """Destructor - called when object is destroyed"""
        self.cleanup()

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
            sensor.set_heart_rate(readings['heart_rate'])
            sensor.set_oxygen_level(readings['spo2'])
            status = sensor.get_status()
            print("Current status:", status)

            time.sleep(2)  # Read every 2 seconds



    except Exception as e:
        print(f"Error: {e}")
    finally:
        # This will always run, even on error
        monitor.cleanup()