import firebase_admin
import sys
import atexit
import signal
import time
import json
import subprocess
import os
from Comms.wifi.server import cred
from sensor.DFRobot_BloodOxygen_S import DFRobot_BloodOxygen_S_i2c


class HeartRateMonitor:
    def __init__(self):
        self.sensor = DFRobot_BloodOxygen_S_i2c(1, 0x57)
        self.initialized = False
        self.ble_process = None

        if self.sensor.begin():
            self.sensor.sensor_start_collect()
            self.initialized = True
            print("Sensor started successfully")

            # Start BLE as separate process
            self.start_ble()

            # Register cleanup handlers
            atexit.register(self.cleanup)
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            print("Sensor initialization failed!")

    def start_ble(self):
        """Start BLE as separate system process"""
        try:
            # Run BLE runner with system Python (not virtual environment)
            ble_script = os.path.join(os.path.dirname(__file__), 'Comms', 'bluetooth', 'ble_runner.py')
            self.ble_process = subprocess.Popen(
                ['python3', ble_script],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            print("BLE process started with system Python")
            time.sleep(2)  # Give BLE time to start
        except Exception as e:
            print(f"Failed to start BLE: {e}")

    def write_sensor_data(self, readings):
        """Write sensor data to shared file for BLE process"""
        try:
            data = {
                'heart_rate': readings['heart_rate'],
                'oxygen_level': readings['spo2'],
                'timestamp': time.time()
            }
            with open('/tmp/sensor_data.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            print(f"Error writing sensor data: {e}")

    def cleanup(self):
        """Properly shutdown everything"""
        if self.ble_process:
            print("Stopping BLE process...")
            self.ble_process.terminate()
            self.ble_process.wait()

        if self.initialized:
            print("Shutting down sensor...")
            self.sensor.sensor_end_collect()
            time.sleep(0.5)
            self.initialized = False

        # Clean up shared file
        try:
            os.remove('/tmp/sensor_data.json')
        except:
            pass

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
            if readings:
                # Write data for BLE process
                monitor.write_sensor_data(readings)

                print(f"Heart Rate: {readings['heart_rate']} bpm")
                print(f"SpO2: {readings['spo2']}%")
                print("-" * 20)

            time.sleep(2)  # Read every 2 seconds

    except Exception as e:
        print(f"Error: {e}")
    finally:
        monitor.cleanup()