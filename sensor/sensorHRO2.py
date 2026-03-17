import sys
import atexit
import time
import json
import os
from sensor.DFRobot_BloodOxygen_S import DFRobot_BloodOxygen_S_i2c


class Sensor:
    """Pure sensor class for heart rate and SpO2 monitoring without BLE dependencies"""

    def __init__(self):
        self._sensor = DFRobot_BloodOxygen_S_i2c(1, 0x57)
        self._initialized = False
        self._running = False

        if self._sensor.begin():
            self._sensor.sensor_start_collect()
            self._initialized = True
            self._running = True
            print("✓ Sensor started successfully")

            # Register cleanup handler only
            atexit.register(self.cleanup)
        else:
            print("✗ Sensor initialization failed!")

    def cleanup(self):
        """Properly shutdown sensor"""
        if not self._running:
            return

        print("🛑 Cleaning up sensor...")

        # Stop sensor
        if self._initialized:
            print("Stopping sensor...")
            self._sensor.sensor_end_collect()
            time.sleep(0.5)
            self._initialized = False

        # Clean up shared file
        try:
            os.remove('/tmp/sensor_data.json')
        except:
            pass

        self._running = False
        print("✓ Sensor cleanup complete")

    def stop(self):
        """Stop the sensor without exiting program"""
        self.cleanup()

    def get_readings(self):
        """Get current sensor readings"""
        if not self._initialized or not self._running:
            return None

        self._sensor.get_heartbeat_SPO2()
        return {
            'heart_rate': self._sensor.heartbeat,
            'spo2': self._sensor.SPO2
        }

    def write_data(self, readings):
        """Write sensor data to shared file"""
        if not self._running:
            return

        try:
            data = {
                'heart_rate': readings['heart_rate'],
                'oxygen_level': readings['spo2'],
                'timestamp': time.time()
            }
            with open('/tmp/sensor_data.json', 'w') as f:
                json.dump(data, f)

        except Exception as e:
            print(f"✗ Error writing sensor data: {e}")

    def check_status(self):
        """Check if sensor is properly initialized and reading data"""
        if not self._initialized:
            return "Sensor not initialized"

        # Try to get a reading
        readings = self.get_readings()
        if readings:
            hr = readings['heart_rate']
            o2 = readings['spo2']

            if hr == -1 and o2 == -1:
                return "Sensor connected but not reading data (both values -1)"
            elif hr == -1:
                return "Sensor connected but HR reading invalid"
            elif o2 == -1:
                return "Sensor connected but O2 reading invalid"
            else:
                return f"Sensor working: HR={hr}, O2={o2}"
        else:
            return "No readings available"

    def __del__(self):
        """Destructor"""
        self.cleanup()