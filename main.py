import firebase_admin
import time
from sensor.hr_monitor import HeartRateMonitor
from Comms.wifi.server import cred

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
        print("-" * 50)

        # Wait a bit for sensor to stabilize
        time.sleep(2)

        while True:
            readings = monitor.get_readings()

            if readings:
                # Display raw readings for debugging
                hr = readings['heart_rate']
                o2 = readings['spo2']

                print(f"Raw Sensor - HR: {hr}, O2: {o2}")

                if hr != -1 and o2 != -1:
                    # Write data for BLE process and update BLE directly
                    monitor.write_sensor_data(readings)

                    # Update BLE characteristics
                    monitor.update_ble_data(hr, o2)

                    print(f"Heart Rate: {hr:3d} bpm")
                    print(f"SpO2: {o2:2d}%")
                    print(f"BLE: Updated successfully")
                    print("\n\n")
                else:
                    print("⏳ No finger detected or waiting for valid readings...")
                    # Update BLE with the current values (even if they're -1)
                    monitor.update_ble_data(hr, o2)

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nStopping health monitor...")
    except Exception as e:
        print(f"!!!Unexpected error!!!: {e}")
        import traceback

        traceback.print_exc()
    finally:
        monitor.cleanup()