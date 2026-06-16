import firebase_admin

class Transmitter:

    def __init__(self, ble_agent, lora_sender):

        self.ble = ble_agent
        self.lora = lora_sender

    def send(self, network, msg):

        try:

            if network == "BLE":
                
                self.ble.update_data(msg["hr"], msg["spo2"])

            elif network == "WIFI":

                from firebase_admin import db
                ref = db.reference("/")
                ref.update({"hr": msg["hr"], "O2": msg["spo2"]})

            elif network == "LORA":

                self.lora.send_health_data(
                    heart_rate= msg["hr"],
                    spo2=msg["spo2"]
                    
                )
            
            return True

        except Exception as e:

            print("Transmission error:", e)

            return False