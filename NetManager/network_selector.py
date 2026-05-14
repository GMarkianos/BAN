import socket
import subprocess
import time
import json
import random

class NetworkSelector:

    def __init__(self, ble_agent, wifi_enabled=True, lora_sender=None):

        self.ble_agent = ble_agent
        self.wifi_enabled = wifi_enabled
        self.lora_sender = lora_sender

        # Reliability tracking
        self.stats_w = {
            "BLE": {"success": 0, "fail": 0},
            "WIFI": {"success": 0, "fail": 0},
            "LORA": {"success": 0, "fail": 0}
        }

        self.stats_m = {
            "BLE": {"success": 0, "fail": 0},
            "WIFI": {"success": 0, "fail": 0},
            "LORA": {"success": 0, "fail": 0}
        }

        # Energy model
        self.consumptions = {
            "BLE": {"base": 0.2, "per_byte": 0.001, "per_sec": 0.05},
            "WIFI": {"base": 1.0, "per_byte": 0.002, "per_sec": 0.2},
            "LORA": {"base": 0.5, "per_byte": 0.0005, "per_sec": 0.1}
        }

        # Static properties (for scoring)
        self.networks = {
            "BLE": {"latency": 0.5, "range": 0.2},
            "WIFI": {"latency": 1.0, "range": 0.5},
            "LORA": {"latency": 0.3, "range": 1.0}
        }

    # ------------------------------
    # MESSAGE CLASSIFICATION
    # ------------------------------

    def classify_message(self, hr, spo2):

        if hr < 40 or hr > 140 or spo2 < 90:
            return "w"
        return "m"

    # ------------------------------
    # RELIABILITY
    # ------------------------------
    def update_stats(self, network, success, msg):
        if success:
            if(msg["type"] == 'w'):
                self.stats_w[network]["success"] += 1
            else:
                self.stats_m[network]["success"] += 1
        else:
            if(msg["type"] == 'w'):
                self.stats_w[network]["fail"] += 1
            else:
                self.stats_m[network]["fail"] += 1

    def get_reliability(self, network, msg):
        if(msg["type"] == 'w'):
            s = self.stats_w[network]["success"]
            f = self.stats_w[network]["fail"]
        else:
            s = self.stats_m[network]["success"]
            f = self.stats_m[network]["fail"]
        if s + f == 0:
            return 0.5

        return s / (s + f)
    # ------------------------------
    #TIME
    # ------------------------------
    def estimate_tx_time(self, network, payload_size):

        speeds = { # bytes/sec
            "BLE": 50000,  
            "WIFI": 1000000,
            "LORA": 3000
        }

        return payload_size / speeds[network]

    # ------------------------------
    # ENERGY
    # ------------------------------
    def estimate_energy(self, network, payload_size, tx_time):
        model = self.consumptions[network]

        return (
            model["base"]
            + model["per_byte"] * payload_size
            + model["per_sec"] * tx_time
        )

    def normalize_energy(self, energy):
        return 1 / (1 + energy) 

    def calc_payload(self, msg):
        return len(json.dumps(msg).encode('utf-8'))
    
    # ------------------------------
    # SIGNAL STRENGTH
    # ------------------------------
    def wifi_strength(self):
        return random.uniform(0.4, 0.9)

    def ble_strength(self):
        return random.uniform(0.3, 0.7)

    def lora_strength(self):
        return random.uniform(0.7, 1.0)

    def get_signal_strength(self, network):
        if network == "WIFI":
            return self.wifi_strength()
        elif network == "BLE":
            return self.ble_strength()
        elif network == "LORA":
            return self.lora_strength()

    # ------------------------------
    # AVAILABILITY
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
            return self.ble_agent is not None
        except:
            return False

    def lora_available(self):
        
        return self.lora_sender is not None

    # ------------------------------
    # SCORING
    # ------------------------------
    def score_network(self, network, available, msg):
        payload = self.calc_payload(msg)
        if not available:
            return -1

        reliability = self.get_reliability(network, msg)
        signal = self.get_signal_strength(network)

        energy_raw = self.estimate_energy(network, payload, tx_time = self.estimate_tx_time(network, payload))
        energy = self.normalize_energy(energy_raw)

        latency = self.networks[network]["latency"]
        range_ = self.networks[network]["range"]

        # Weights depending on message type
        if msg["type"] == "m":
            w = {
                "reliability": 0.3,
                "signal": 0.2,
                "range": 0.2,
                "energy": 0.3,
                "latency": 0.1
            }
        else:  # WARNING
            w = {
                "reliability": 0.4,
                "signal": 0.2,
                "range": 0.2,
                "energy": 0.1,
                "latency": 0.3
            }

        score = (
            w["reliability"] * reliability
            + w["signal"] * signal
            + w["range"] * range_
            + w["energy"] * energy
            - w["latency"] * latency
        )

        return score

    # ------------------------------
    # SELECT BEST NETWORK
    # ------------------------------
    def choose_network(self, msg):

        availability = {
            "BLE": self.ble_available(),
            "WIFI": self.wifi_available(),
            "LORA": self.lora_available()
        }

        scores = {}

        for net in availability:
            scores[net] = self.score_network(net, availability[net], msg)

        valid_scores = {k: v for k, v in scores.items() if v >= 0}

        sorted_nets = sorted(valid_scores, key=valid_scores.get, reverse=True)

        best = sorted_nets[0] if len(sorted_nets) > 0 else None
        second = sorted_nets[1] if len(sorted_nets) > 1 else None

        if best is None: 
            return None, None

        if scores[best] < 0:
            return None, None

        return best, second