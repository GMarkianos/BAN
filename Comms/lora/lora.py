#!/usr/bin/env python3
"""
LoRa Module Library for DX-LR02-900T22D
Simple transparent UART bridge without AT commands
"""

import RPi.GPIO as GPIO
import serial
import time
import json
import threading
from queue import Queue, Empty


class LoRaModule:
    """
    Main LoRa communication class
    Handles transparent UART communication with DX-LR02-900T22D
    """
    
    def __init__(self, m0_pin=25, m1_pin=23, aux_pin=24, 
                 port='/dev/serial0', baud=9600):
        """
        Initialize LoRa module
        
        Args:
            m0_pin: GPIO pin for M0 (mode select bit 0)
            m1_pin: GPIO pin for M1 (mode select bit 1)  
            aux_pin: GPIO pin for AUX (optional, not used if not connected)
            port: UART device path
            baud: Baud rate (module default is 9600)
        """
        self.m0_pin = m0_pin
        self.m1_pin = m1_pin
        self.aux_pin = aux_pin
        self.port = port
        self.baud = baud
        
        self.ser = None
        self.tx_queue = Queue()
        self.rx_queue = Queue()
        self.running = False
        self.lock = threading.Lock()
        self._threads = []
        
        self._setup_gpio()
        
    def _setup_gpio(self):
        """Configure GPIO pins"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(self.m0_pin, GPIO.OUT)
        GPIO.setup(self.m1_pin, GPIO.OUT)
        GPIO.setup(self.aux_pin, GPIO.IN)
        self._set_normal_mode()
        
    def _set_normal_mode(self):
        """Set module to transparent transmission mode (M1=0, M0=0)"""
        GPIO.output(self.m1_pin, GPIO.LOW)
        GPIO.output(self.m0_pin, GPIO.LOW)
        time.sleep(0.1)
        
    def connect(self):
        """
        Open serial connection and start worker threads
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1
            )
            self.running = True
            
            # Start background threads
            self._threads = [
                threading.Thread(target=self._tx_worker, daemon=True),
                threading.Thread(target=self._rx_worker, daemon=True)
            ]
            for t in self._threads:
                t.start()
                
            return True
        except Exception as e:
            print(f"[LoRa] Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Stop threads, close serial, cleanup GPIO"""
        self.running = False
        
        for t in self._threads:
            t.join(timeout=2)
            
        if self.ser and self.ser.is_open:
            self.ser.close()
            
        GPIO.cleanup()
        
    def send(self, data):
        """
        Queue data for transmission
        
        Args:
            data: String or dictionary (dict will be JSON-encoded)
        """
        if isinstance(data, dict):
            data = json.dumps(data)
        self.tx_queue.put(str(data))
        
    def get_messages(self, clear=True):
        """
        Retrieve received messages
        
        Args:
            clear: If True, removes messages from queue (default)
            
        Returns:
            list: Received messages as strings
        """
        messages = []
        while not self.rx_queue.empty():
            messages.append(self.rx_queue.get())
            if not clear:
                self.rx_queue.put(messages[-1])  # Put back if not clearing
        return messages
        
    def _tx_worker(self):
        """Internal: Background transmitter thread"""
        while self.running:
            try:
                message = self.tx_queue.get(timeout=0.1)
                with self.lock:
                    time.sleep(0.05)  # Brief delay for module readiness
                    self.ser.write(message.encode('utf-8'))
                    self.ser.flush()
            except Empty:
                continue
            except Exception as e:
                print(f"[LoRa TX Error] {e}")
                
    def _rx_worker(self):
        """Internal: Background receiver thread"""
        while self.running:
            try:
                with self.lock:
                    if self.ser.in_waiting > 0:
                        data = self.ser.read(self.ser.in_waiting)
                        try:
                            text = data.decode('utf-8')
                            self.rx_queue.put(text)
                        except UnicodeDecodeError:
                            self.rx_queue.put(f"[HEX]{data.hex()}")
                time.sleep(0.01)
            except Exception as e:
                print(f"[LoRa RX Error] {e}")


class LoRaHealthSender(LoRaModule):
    """
    Specialized class for sending health sensor data
    Extends base LoRaModule with health-specific formatting
    """
    
    def __init__(self, device_id="pi_zero_health", **kwargs):
        """
        Initialize health sender
        
        Args:
            device_id: Unique identifier for this device
            **kwargs: Passed to parent LoRaModule (pins, port, etc.)
        """
        super().__init__(**kwargs)
        self.device_id = device_id
        
    def send_health_data(self, heart_rate, spo2, timestamp=None, extra=None):
        """
        Send health sensor data as JSON packet
        
        Args:
            heart_rate: Heart rate in BPM
            spo2: Blood oxygen percentage
            timestamp: Unix timestamp (auto-generated if None)
            extra: Optional dict with additional fields
        """
        if timestamp is None:
            timestamp = time.time()
            
        packet = {
            "ts": timestamp,
            "hr": heart_rate,
            "spo2": spo2,
            "dev": self.device_id
        }
        
        if extra and isinstance(extra, dict):
            packet.update(extra)
            
        self.send(packet)
        
    def send_alert(self, alert_type, message):
        """
        Send alert notification
        
        Args:
            alert_type: Type of alert (e.g., "high_hr", "low_spo2")
            message: Human-readable alert message
        """
        packet = {
            "type": "alert",
            "alert_type": alert_type,
            "msg": message,
            "ts": time.time(),
            "dev": self.device_id
        }
        self.send(packet)


class LoRaReceiver(LoRaModule):
    """
    Specialized class for receiving and processing data
    Extends base LoRaModule with parsing capabilities
    """
    
    def __init__(self, on_health_data=None, on_alert=None, on_raw=None, **kwargs):
        """
        Initialize receiver with callbacks
        
        Args:
            on_health_data: Function to call when health data received
            on_alert: Function to call when alert received  
            on_raw: Function to call for any raw message
            **kwargs: Passed to parent LoRaModule
        """
        super().__init__(**kwargs)
        self.on_health_data = on_health_data
        self.on_alert = on_alert
        self.on_raw = on_raw
        
    def process_messages(self):
        """
        Check for messages and trigger appropriate callbacks
        Call this regularly in your main loop
        """
        messages = self.get_messages()
        
        for msg in messages:
            # Call raw handler if provided
            if self.on_raw:
                self.on_raw(msg)
                
            # Try to parse as JSON
            try:
                data = json.loads(msg)
                
                if data.get("type") == "alert" and self.on_alert:
                    self.on_alert(data)
                elif "hr" in data and self.on_health_data:
                    self.on_health_data(data)
                    
            except json.JSONDecodeError:
                # Not JSON, already handled by on_raw
                pass