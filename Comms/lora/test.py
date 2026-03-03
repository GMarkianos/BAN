#!/usr/bin/env python3
"""
DX-LR02-900T22D - Working Transparent Mode Only
No AT commands, no config mode needed
"""

import RPi.GPIO as GPIO
import serial
import time
import json
import threading
from queue import Queue

# Pin configuration (your current wiring)
M0_PIN = 25       # GPIO 25 (Pin 22)
M1_PIN = 23       # GPIO 23 (Pin 16)
AUX_PIN = 24      # GPIO 24 (Pin 18) - optional, not used

UART_PORT = '/dev/serial0'
UART_BAUD = 9600  # Default, module likely auto-negotiates

class LoRaTransparent:
    """
    Simple transparent UART LoRa bridge
    Works with DX-LR02-900T22D without AT commands
    """
    
    def __init__(self):
        self.ser = None
        self.tx_queue = Queue()
        self.rx_queue = Queue()
        self.running = False
        self.lock = threading.Lock()
        
        # Setup GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(M0_PIN, GPIO.OUT)
        GPIO.setup(M1_PIN, GPIO.OUT)
        GPIO.setup(AUX_PIN, GPIO.IN)  # Monitor if available
        
        # Set to normal mode (transparent)
        self._set_normal_mode()
        
    def _set_normal_mode(self):
        """M1=0, M0=0 for transparent transmission"""
        GPIO.output(M1_PIN, GPIO.LOW)
        GPIO.output(M0_PIN, GPIO.LOW)
        time.sleep(0.1)
        print("[LoRa] Normal (transparent) mode active")
        
    def connect(self):
        """Open serial connection"""
        try:
            self.ser = serial.Serial(
                port=UART_PORT,
                baudrate=UART_BAUD,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=0.1  # Non-blocking for polling
            )
            self.running = True
            
            # Start background threads
            self.rx_thread = threading.Thread(target=self._rx_worker, daemon=True)
            self.tx_thread = threading.Thread(target=self._tx_worker, daemon=True)
            self.rx_thread.start()
            self.tx_thread.start()
            
            print(f"[LoRa] Connected on {UART_PORT} @ {UART_BAUD}")
            return True
        except Exception as e:
            print(f"[LoRa] Connection failed: {e}")
            return False
            
    def disconnect(self):
        """Clean shutdown"""
        self.running = False
        if hasattr(self, 'rx_thread'):
            self.rx_thread.join(timeout=2)
        if hasattr(self, 'tx_thread'):
            self.tx_thread.join(timeout=2)
        if self.ser:
            self.ser.close()
        GPIO.cleanup()
        print("[LoRa] Disconnected")
        
    def _tx_worker(self):
        """Background transmitter"""
        while self.running:
            try:
                message = self.tx_queue.get(timeout=0.1)
                with self.lock:
                    # Simple delay instead of AUX check (AUX not working)
                    time.sleep(0.05)
                    self.ser.write(message.encode('utf-8'))
                    self.ser.flush()
                    print(f"[TX] {len(message)} bytes")
            except:
                continue
                
    def _rx_worker(self):
        """Background receiver"""
        while self.running:
            try:
                with self.lock:
                    if self.ser.in_waiting > 0:
                        data = self.ser.read(self.ser.in_waiting)
                        try:
                            text = data.decode('utf-8')
                            self.rx_queue.put(text)
                            print(f"[RX] {text[:60]}...")
                        except:
                            self.rx_queue.put(data.hex())  # Raw hex if not text
                time.sleep(0.01)
            except:
                continue
                
    def send(self, data):
        """Queue data for transmission"""
        if isinstance(data, dict):
            data = json.dumps(data)
        self.tx_queue.put(str(data))
        
    def get_messages(self):
        """Get all pending received messages"""
        messages = []
        while not self.rx_queue.empty():
            messages.append(self.rx_queue.get())
        return messages

# ============ INTEGRATION WITH YOUR HEALTH PROJECT ============

class HealthMonitorWithLoRa:
    """
    Example integration with your heart rate + SpO2 sensor
    """
    
    def __init__(self):
        self.lora = LoRaTransparent()
        
    def start(self):
        if not self.lora.connect():
            print("Warning: LoRa not available, continuing with local logging only")
            
        try:
            while True:
                # === YOUR EXISTING SENSOR CODE HERE ===
                # Example: hr, spo2 = read_max30102()
                hr = 72      # Replace with actual sensor reading
                spo2 = 98    # Replace with actual sensor reading
                
                # Create data packet
                packet = {
                    "ts": time.time(),
                    "hr": hr,
                    "spo2": spo2,
                    "dev": "pi_zero_health"
                }
                
                # Send via LoRa
                self.lora.send(packet)
                print(f"Sent: HR={hr}, SpO2={spo2}")
                
                # Check for incoming commands/config
                messages = self.lora.get_messages()
                for msg in messages:
                    self._handle_command(msg)
                    
                time.sleep(5)  # Adjust sampling rate as needed
                
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            self.lora.disconnect()
            
    def _handle_command(self, msg):
        """Handle incoming commands"""
        print(f"Received command: {msg}")
        # Add command parsing logic here (e.g., change sampling rate)

# ============ GATEWAY CODE (for your PC) ============

class LoRaGateway:
    """
    Run this on a second Pi or PC with LoRa module
    Receives LoRa data and forwards to your PC via MQTT/HTTP
    """
    
    def __init__(self):
        self.lora = LoRaTransparent()
        # Optional: MQTT to forward to your PC
        # import paho.mqtt.client as mqtt
        # self.mqtt = mqtt.Client()
        
    def run(self):
        if not self.lora.connect():
            return
            
        print("Gateway running - forwarding LoRa to console")
        print("You can add MQTT/HTTP forwarding here\n")
        
        try:
            while True:
                messages = self.lora.get_messages()
                for msg in messages:
                    print(f"[GATEWAY RX] {msg}")
                    
                    # Parse JSON health data
                    try:
                        data = json.loads(msg)
                        if 'hr' in data:
                            print(f"  Health Data: HR={data['hr']}, SpO2={data['spo2']}")
                            # Forward to your PC here via MQTT/HTTP/WebSocket
                    except:
                        pass
                        
                time.sleep(0.1)
        except KeyboardInterrupt:
            pass
        finally:
            self.lora.disconnect()

# ============ TEST FUNCTIONS ============

def test_loopback():
    """Test with single module (just sends data)"""
    print("=== LoRa Loopback Test ===")
    print("This will send test messages every 2 seconds")
    print("If you have a second module, you should see them there\n")
    
    lora = LoRaTransparent()
    if not lora.connect():
        return
        
    try:
        for i in range(10):
            msg = f"TEST{i}:PiZero2W_{time.time()}"
            lora.send(msg)
            print(f"Sent: {msg}")
            
            # Check for any echo/reply
            time.sleep(2)
            rx = lora.get_messages()
            for r in rx:
                print(f"  Received: {r}")
    finally:
        lora.disconnect()

def test_health_simulation():
    """Simulate health monitoring"""
    print("=== Health Monitor Simulation ===")
    monitor = HealthMonitorWithLoRa()
    monitor.start()

def run_gateway():
    """Run as gateway receiver"""
    print("=== LoRa Gateway ===")
    gateway = LoRaGateway()
    gateway.run()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python3 2.py test     - Send test messages")
        print("  python3 2.py health   - Simulate health monitor")
        print("  python3 2.py gateway  - Run as gateway receiver")
    else:
        cmd = sys.argv[1]
        if cmd == "test":
            test_loopback()
        elif cmd == "health":
            test_health_simulation()
        elif cmd == "gateway":
            run_gateway()
        else:
            print(f"Unknown command: {cmd}")
