import firebase_admin
import time
from sensor.hr_monitor import HeartRateMonitor
from Comms.wifi.server import cred
from Comms.lora import lora
# Main program
if __name__ == "__main__":
    monitor = HeartRateMonitor()

    try:
        # Initialize Firebase
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"
            })

        lora = LoRaHealthSender(
            device_id="01",
            m0_pin=25,      # Your GPIO 25
            m1_pin=23,      # Your GPIO 23
            aux_pin=24,     # Your GPIO 24
            port='/dev/serial0',
            baud=9600
        )
        try: 
            lora.connect()
        except Exception as e:
            print(f"LoRa error: {e}")
        # Wait a bit for sensor to stabilize
        time.sleep(2)

        while True:
            readings = monitor.get_readings()

            if readings:
                # Display raw readings for debugging
                #hr = readings['heart_rate']
                #o2 = readings['spo2']

                print(f"Raw Sensor - HR: {hr}, O2: {o2}")

                if hr != -1 and o2 != -1:
                    # Write data for BLE process and update BLE directly
                    monitor.write_sensor_data(readings)
                    
                    lora.send_health_data(
                        heart_rate=hr,
                        spo2=o2
                    )

                    # Update BLE characteristics
                    monitor.update_ble_data(hr, o2)

                    ref = db.reference("/")
                    ref.update({"O2" : o2})
                    ref.update({"hr": hr})
                    
                    print("\n\n")
                else:
                    print("No finger detected or waiting for valid readings...")
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