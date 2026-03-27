import firebase_admin

class Transmitter:

    def __init__(self, ble_agent, lora_sender):

        self.ble = ble_agent
        self.lora = lora_sender

    def send(self, network, hr, spo2):

        try:

            if network == "BLE":

                self.ble_agent.update_data(hr, spo2)

            elif network == "WIFI":

                from firebase_admin import db
                ref = db.reference("/")
                ref.update({"hr": hr, "O2": spo2})

            elif network == "LORA":

                self.lora.send_health_data(
                    heart_rate=hr,
                    spo2=spo2
                )

            return True

        except Exception as e:

            print("Transmition error:", e)

            return False