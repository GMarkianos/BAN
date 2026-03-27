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
    
    try:

        # Start BLE service
        ble_agent.start()

        # Wait a bit for sensor to stabilize
        time.sleep(2)

        while running:
            readings = sensor.get_readings()

            hr = readings['heart_rate']
            o2 = readings['spo2']
            print(hr,o2)
            msg_type = selector.classify_message(hr, o2)

            network = selector.choose_network(msg_type)

            print("Message type:", msg_type)
            print("Selected network:", network)

            success = False
            if not queue.empty():

                msg = queue.get()

                network = selector.choose_network("MONITORING")

                if network:
                    transmitter.send(network, msg["hr"], msg["spo2"])
            elif network:

                success = transmitter.send(network, hr, o2)

            if not success:

                queue.add(hr, o2)

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