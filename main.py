import firebase_admin
import time
import signal
import sys
from firebase_admin import db
from sensor.sensorHRO2 import Sensor
from Comms.bluetooth.ble_agent import BLEAgent
from Comms.wifi.server import cred
from Comms.lora.lora import LoRaHealthSender

# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    print("\n🛑 Received shutdown signal...")
    running = False

# Register signal handlers
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Main program
if __name__ == "__main__":
    # Initialize separate entities
    sensor = Sensor()
    ble_agent = BLEAgent()
    lora_sender = None

    try:
        # Initialize Firebase
        if not firebase_admin._apps:
            firebase_admin.initialize_app(cred, {
                "databaseURL": "https://ban-net-default-rtdb.europe-west1.firebasedatabase.app/"
            })

        # Initialize LoRa
        try:
            lora_sender = LoRaHealthSender(
                device_id="01",
                m0_pin=25,      # Your GPIO 25
                m1_pin=23,      # Your GPIO 23
                aux_pin=24,     # Your GPIO 24
                port='/dev/serial0',
                baud=9600
            )
            lora_sender.connect()
        except Exception as e:
            print(f"LoRa initialization error: {e}")
            lora_sender = None

        # Start BLE service
        ble_agent.start()

        # Wait a bit for sensor to stabilize
        time.sleep(2)

        while running:
            readings = sensor.get_readings()

            if readings:
                hr = readings['heart_rate']
                o2 = readings['spo2']

                print(f"Raw Sensor - HR: {hr}, O2: {o2}")

                if hr != -1 and o2 != -1:
                    # Write data to shared file (handled by sensor)
                    sensor.write_data(readings)

                    # Send via LoRa (if initialized)
                    if lora_sender:
                        try:
                            lora_sender.send_health_data(
                                heart_rate=hr,
                                spo2=o2
                            )
                        except Exception as e:
                            print(f"LoRa send error: {e}")

                    # Update BLE characteristics (handled by ble_agent)
                    ble_agent.update_data(hr, o2)

                    # Update Firebase
                    try:
                        ref = db.reference("/")
                        ref.update({"O2": o2})
                        ref.update({"hr": hr})
                    except Exception as e:
                        print(f"Firebase update error: {e}")

                    print("\n\n")
                else:
                    print("No finger detected or waiting for valid readings...")
                    # Update BLE with the current values (even if they're -1)
                    ble_agent.update_data(hr, o2)

            time.sleep(3)

    except KeyboardInterrupt:
        print("\nStopping health monitor...")
    except Exception as e:
        print(f"!!!Unexpected error!!!: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Stop both components
        sensor.stop()
        ble_agent.stop()
        print("\n✓ Program terminated cleanly")