import firebase_admin
import time
import signal
import sys
from firebase_admin import db
from sensor.sensorHRO2 import Sensor
from Comms.bluetooth.ble_agent import BLEAgent
from Comms.wifi.server import cred
from Comms.lora.lora import LoRaHealthSender
from NetManager.transmitter import Transmitter
from NetManager.network_selector import NetworkSelector
from NetManager.mqueue import MessageQueue
# Global flag for clean shutdown
running = True

def signal_handler(sig, frame):
    """Handle shutdown signals gracefully"""
    global running
    print("\n Received shutdown signal...")
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
    except Exception as e:
        print(f"!!!Unexpected firebse error!!!: {e}")
        import traceback
        traceback.print_exc()
    try:
        # Start BLE service
        ble_agent.start()

        #Initialize LoRa
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

    selector = NetworkSelector(ble_agent, True, lora_sender)
    transmitter = Transmitter(ble_agent, lora_sender)
    queue = MessageQueue()
    
    # Wait a bit for sensor to stabilize
    time.sleep(2)

    try:

        while running:
            readings = sensor.get_readings()

            hr = readings['heart_rate']
            o2 = readings['spo2']
            msg_type = selector.classify_message(hr, o2)
            msg = {"hr": hr, "spo2": o2,"type": msg_type}


            success = False
            best, second = selector.choose_network(msg)
            '''if not queue.empty():

                msg = queue.get()

                best, second = selector.choose_network(msg)
                if msg["type"] == "w" and best:
                    success1 = transmitter.send(best,msg)
                    success2 = transmitter.send(second, msg) if second else False

                    selector.update_stats(best, success1,msg["type"])
                    if second:
                        selector.update_stats(second, success2,msg)["type"]

                    success = success1 or success2 
                else:
                    success = transmitter.send(best, msg)
                    selector.update_stats(best, success ,msg["type"])

            elif best:'''
            if msg["type"] == "w" and best:
                success1 = transmitter.send(best,msg)
                success2 = transmitter.send(second, msg) if second else False

                selector.update_stats(best, success1, msg["type"])
                if second:
                    selector.update_stats(second, success2, msg["type"])

                success = success1 or success2 
            else:
                success = transmitter.send(best, msg)
                selector.update_stats(best, success, msg["type"])

            if best:
                print("Message type:", msg["type"])
                print("Selected network:", best)
            if not success:

                queue.add(msg)

            time.sleep(1)

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