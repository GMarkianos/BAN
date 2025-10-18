#!/usr/bin/env python3
# ble_runner.py - Runs with system Python

import sys
import json
import time
from ble_sensor_lib import BLESensorManager


def main():
    ble_manager = BLESensorManager("HealthSensor")

    if not ble_manager.start_advertising():
        print("Failed to start BLE")
        return 1

    print("BLE advertising started. Waiting for sensor data...")

    try:
        while True:
            # Read sensor data from shared file
            try:
                with open('/tmp/sensor_data.json', 'r') as f:
                    sensor_data = json.load(f)

                # Update BLE characteristics
                ble_manager.set_heart_rate(sensor_data['heart_rate'])
                ble_manager.set_oxygen_level(sensor_data['oxygen_level'])
                print(f"BLE: HR {sensor_data['heart_rate']}, O2 {sensor_data['oxygen_level']}")

            except FileNotFoundError:
                pass  # No data yet

            time.sleep(2)

    except KeyboardInterrupt:
        print("\nStopping BLE...")
    finally:
        ble_manager.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())