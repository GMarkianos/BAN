import socket
import subprocess
import time

class NetworkSelector:

    def __init__(self, ble_agent, wifi_enabled=True, lora_sender=None):

        self.ble_agent = ble_agent
        self.wifi_enabled = wifi_enabled
        self.lora_sender = lora_sender

        self.networks = {
            "BLE": {"energy": 1, "latency": 2, "range": 1},
            "WIFI": {"energy": 3, "latency": 1, "range": 2},
            "LORA": {"energy": 2, "latency": 3, "range": 3}
        }

    # ------------------------------
    # MESSAGE CLASSIFICATION
    # ------------------------------

    def classify_message(self, hr, spo2):

        if hr < 40 or hr > 140 or spo2 < 90:
            return "WARNING"

        return "MONITORING"

    # ------------------------------
    # NETWORK AVAILABILITY
    # ------------------------------

    def wifi_available(self):

        if not self.wifi_enabled:
            return False

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except:
            return False

    def ble_available(self):

        try:
            return self.ble_agent._initialized()
        except:
            return False

    def lora_available(self):

        return self.lora_sender is not None

    # ------------------------------
    # NETWORK SCORING
    # ------------------------------

    def score_network(self, network, message_type, available):

        if not available:
            return -1

        props = self.networks[network]

        energy = props["energy"]
        latency = props["latency"]
        range_ = props["range"]

        if message_type == "MONITORING":

            score = (
                (5 - energy) * 3 +
                (5 - latency) * 1 +
                (5 - range_) * 1
            )

        else:  # WARNING

            score = (
                (5 - latency) * 4 +
                (5 - range_) * 3 +
                (5 - energy) * 1
            )

        return score

    # ------------------------------
    # SELECT BEST NETWORK
    # ------------------------------

    def choose_network(self, message_type):

        availability = {
            "BLE": self.ble_available(),
            "WIFI": self.wifi_available(),
            "LORA": self.lora_available()
        }

        scores = {}

        for net in availability:

            score = self.score_network(
                net,
                message_type,
                availability[net]
            )

            scores[net] = score

        optimal_network = max(scores, key=scores.get)

        if scores[optimal_network] < 0:
            return None

        '''return optimal_network'''
        return "LORA"