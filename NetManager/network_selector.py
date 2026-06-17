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
        
        self.demo = None
        self.counter = 0
        self.flag = False

        # Reliability tracking
        self.stats_w = {
            "BLE": {"success": 5, "fail": 5},
            "WIFI": {"success": 5, "fail": 5},
            "LORA": {"success": 5, "fail": 5}
        }

        self.stats_m = {
            "BLE": {"success": 5, "fail": 5},
            "WIFI": {"success": 5, "fail": 5},
            "LORA": {"success": 5, "fail": 5}
        }

        # Energy model
        self.consumptions = {
            "BLE": {"base": 0.2, "per_byte": 0.001, "per_sec": 0.05},
            "WIFI": {"base": 1.0, "per_byte": 0.002, "per_sec": 0.2},
            "LORA": {"base": 0.5, "per_byte": 0.0005, "per_sec": 0.1}
        }

        # Static properties (for scoring)
        self.networks = {
            "BLE": {"latency": 0.9, "range": 0.2},
            "WIFI": {"latency": 0.5, "range": 0.7},
            "LORA": {"latency": 0.2, "range": 1.0}
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
    def get_bettery_level(self):
        if self.demo:
            return self.demo["battery"]
        
        return 100
    
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
        try:
            output = subprocess.check_output(
                ["iw", "dev", "wlan0", "link"],
                stderr=subprocess.DEVNULL
            ).decode()
            
            match = re.search(r"signal: (-\d+) dBm", output)
            if match:
                dbm = int(match.group(1))
                return max(0.0, min(1.0, (dbm + 90) / 40))
            return 0.5
        except:
            return 0.5

    def ble_strength(self):
        try:
            from Comms.bluetooth.bletools import BleTools
            import dbus
            bus = BleTools.get_bus()
            remote_om = dbus.Interface(bus.get_object("org.bluez", "/"),
                                    "org.freedesktop.DBus.ObjectManager")
            objects = remote_om.GetManagedObjects()
            
            for path, props in objects.items():
                if "org.bluez.Device1" in props:
                    device = props["org.bluez.Device1"]
                    if device.get("Connected") and "RSSI" in device:
                        rssi = int(device["RSSI"])
                        return max(0.0, min(1.0, (rssi + 90) / 40))
            
            return 0.5  # no client connected, honest fallback
        except:
            return 0.5
        
    def lora_strength(self):
        return 0.7

    def get_signal_strength(self, network):
        if self.demo:

            return {
                "BLE": self.demo["ble_signal"],
                "WIFI": self.demo["wifi_signal"],
                "LORA": self.demo["lora_signal"]
            }[network]
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
        if self.demo:
            return self.demo["wifi_available"]
        
        if not self.wifi_enabled:
            return False

        try:
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            return True
        except:
            return False

    def ble_available(self):
        if self.demo:
            return self.demo["ble_available"]
        
        try:
            return self.ble_agent is not None and self.ble_agent.is_running()
        except:
            return False

    def lora_available(self):
        if self.demo:
            return self.demo["lora_available"]

        return self.lora_sender is not None

    # ------------------------------
    # SCORING
    # ------------------------------
    def score_network(self, network, available, msg):
        payload = self.calc_payload(msg)
        if not available:
            return -1

        if self.demo:
            battery = self.demo["battery"]

        else:
            battery = 100
    
        reliability = self.get_reliability(network, msg)
        if self.demo and self.demo["swich"]==True: 
            print({reliability})
        signal = self.get_signal_strength(network)

        energy_raw = self.estimate_energy(network, payload, tx_time = self.estimate_tx_time(network, payload))
        energy = self.normalize_energy(energy_raw)

        latency = self.networks[network]["latency"]
        range_ = self.networks[network]["range"]

        # Weights depending on message type
        if msg["type"] == "m":
            if battery < 20:

                w = {
                    "reliability":0.2,
                    "signal":0.1,
                    "range":0.15,
                    "energy":0.4,
                    "latency":0.15
                }
            else:
                w = {
                    "reliability": 0.15,
                    "signal":      0.1,
                    "range":       0.20,
                    "energy":      0.3,
                    "latency":     0.25
            }
        else:  # WARNING
            w = {
                "reliability": 0.4,
                "signal":      0.15,
                "range":       0.25,
                "energy":      0.1,
                "latency":     0.1
            }

        score = (
            w["reliability"] * reliability
            + w["signal"] * signal
            + w["range"] * range_
            + w["energy"] * energy
            + w["latency"] * latency
        )
        
        return score

    # ------------------------------
    # SELECT BEST NETWORK
    # ------------------------------
    def choose_network(self, msg):
        if self.demo and self.demo.get("switch"):

            self.counter += 1

            if self.counter > 5:
                self.flag = True
#"BLE": (False if self.flag else self.ble_available()),
        availability = {
            "BLE":  self.ble_available(),
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