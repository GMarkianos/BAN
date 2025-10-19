import firebase_admin
import sys
import atexit
import signal
import time
import json
import subprocess
import os
import threading
from Comms.wifi.server import cred
from sensor.DFRobot_BloodOxygen_S import DFRobot_BloodOxygen_S_i2c

# Import the BLE components
from Comms.bluetooth.service import Application
from Comms.bluetooth.sensor import SensorService, HRCharacteristic, O2Characteristic


class HeartRateMonitor:
    def __init__(self):
        self.sensor = DFRobot_BloodOxygen_S_i2c(1, 0x57)
        self.initialized = False

        # BLE Components
        self.ble_app = None
        self.ble_hr_characteristic = None
        self.ble_o2_characteristic = None
        self.ble_thread = None
        self.ble_running = False

        if self.sensor.begin():
            self.sensor.sensor_start_collect()
            self.initialized = True
            print("✓ Sensor started successfully")

            # Initialize BLE
            self.start_ble_service()

            # Register cleanup handlers
            atexit.register(self.cleanup)
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)
        else:
            print("✗ Sensor initialization failed!")

    def start_ble_service(self):
        """Start BLE service integrated with main application"""
        try:
            # Create and setup BLE application
            self.ble_app = Application()
            sensor_service = SensorService(0)
            self.ble_app.add_service(sensor_service)

            # Get references to characteristics for updating values
            for characteristic in sensor_service.characteristics:
                if isinstance(characteristic, HRCharacteristic):
                    self.ble_hr_characteristic = characteristic
                elif isinstance(characteristic, O2Characteristic):
                    self.ble_o2_characteristic = characteristic

            # Register BLE application
            self.ble_app.register()

            # Start BLE in a separate thread to not block main loop
            self.ble_running = True
            self.ble_thread = threading.Thread(target=self._run_ble, daemon=True)
            self.ble_thread.start()

            print("✓ BLE service started successfully")
            time.sleep(2)  # Give BLE time to initialize
        except Exception as e:
            print(f"✗ Failed to start BLE service: {e}")

    def _run_ble(self):
        """Run BLE mainloop in separate thread"""
        try:
            self.ble_app.run()
        except Exception as e:
            print(f"BLE thread error: {e}")
        finally:
            self.ble_running = False

    def update_ble_data(self, heart_rate, oxygen_level):
        """Update BLE characteristics with new sensor data"""
        if self.ble_hr_characteristic:
            self.ble_hr_characteristic.set_heart_rate(heart_rate)
        if self.ble_o2_characteristic:
            self.ble_o2_characteristic.set_oxygen_level(oxygen_level)

    def write_sensor_data(self, readings):
        """Write sensor data to shared file and update BLE"""
        try:
            data = {
                'heart_rate': readings['heart_rate'],
                'oxygen_level': readings['spo2'],
                'timestamp': time.time()
            }
            with open('/tmp/sensor_data.json', 'w') as f:
                json.dump(data, f)

            # Also update BLE characteristics directly
            self.update_ble_data(readings['heart_rate'], readings['spo2'])

        except Exception as e:
            print(f"✗ Error writing sensor data: {e}")

    def cleanup(self):
        """Properly shutdown everything"""
        print("🛑 Cleaning up...")

        # Stop BLE service
        if self.ble_app:
            print("Stopping BLE service...")
            self.ble_app.quit()
            self.ble_running = False

        # Stop sensor
        if self.initialized:
            print("Stopping sensor...")
            self.sensor.sensor_end_collect()
            time.sleep(0.5)
            self.initialized = False

        # Clean up shared file
        try:
            os.remove('/tmp/sensor_data.json')
        except:
            pass

        print("✓ Cleanup complete")

    def signal_handler(self, sig, frame):
        """Handle Ctrl+C and other termination signals"""
        print("\n🛑 Received shutdown signal...")
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
        """Destructor"""
        self.cleanup()


# Main program
if __name__ == "__main__":
    monitor = HeartRateMonitor()

    try:
        # Initialize Firebase
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"
            })

        print("🚀 Health Monitor Running...")
        print("Press Ctrl+C to stop")
        print("Look for 'HealthSensor' in nRF Connect")

        while True:
            readings = monitor.get_readings()

            if readings:
                # Write data for BLE process and update BLE directly
                monitor.write_sensor_data(readings)

                # Display current readings
                hr = readings['heart_rate']
                o2 = readings['spo2']

                if hr != -1 and o2 != -1:
                    print(f"❤️  Heart Rate: {hr:3d} bpm")
                    print(f"💨 SpO2: {o2:2d}%")
                    print(f"📡 BLE: Active - HR: {hr}bpm, O2: {o2}%")
                    print("-" * 25)
                else:
                    print("⏳ Waiting for valid sensor readings...")

            time.sleep(2)

    except KeyboardInterrupt:
        print("\n🛑 Stopping health monitor...")
    except Exception as e:
        print(f"💥 Unexpected error: {e}")
    finally:
        monitor.cleanup()