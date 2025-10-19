#!/usr/bin/env python3
import sys
import time
import json
import os
from gobject_ble_lib import BLEManager


def main():
    print("=== BLE Health Monitor ===")

    ble = BLEManager("BAN-HealthSensor")

    if not ble.start_advertising():
        print("Failed to start BLE advertising")
        return 1

    print("BLE advertising active")
    print("Look for 'BAN-HealthSensor' in nRF Connect")
    print("Press Ctrl+C to stop")

    try:
        while True:
            # Read sensor data from shared file
            try:
                with open('/tmp/sensor_data.json', 'r') as f:
                    sensor_data = json.load(f)

                hr = sensor_data.get('heart_rate', -1)
                o2 = sensor_data.get('oxygen_level', -1)

                # Update BLE with valid sensor data
                if hr != -1 and o2 != -1:
                    ble.set_heart_rate(hr)
                    ble.set_oxygen_level(o2)
                    print(f"📊 BLE Updated - HR: {hr}bpm, O2: {o2}%")
                else:
                    print("⏳ Waiting for valid sensor data...")

            except FileNotFoundError:
                print("⏳ Waiting for sensor data file...")
            except json.JSONDecodeError:
                print("⚠ Corrupted sensor data file")
            except Exception as e:
                print(f"📖 Data read error: {e}")

            time.sleep(3)

    except KeyboardInterrupt:
        print("\n🛑 Stopping BLE...")
    finally:
        ble.stop()

    return 0


if __name__ == "__main__":
    sys.exit(main())