#!/usr/bin/env python3
import dbus
import dbus.mainloop.glib
import json
import time
import subprocess
import threading
from gi.repository import GLib


class BLEManager:
    """
    BLE Manager using PyGObject and dbus (without dbus.service)
    Provides heart rate and SpO2 data via BLE advertising
    """

    def __init__(self, device_name="HealthMonitor"):
        self.device_name = device_name
        self.heart_rate = 72
        self.oxygen_level = 98
        self.is_running = False
        self.mainloop = None
        self.adv_thread = None

    def start_advertising(self):
        """Start BLE advertising with device name and sensor data"""
        try:
            print(f"Starting BLE advertising: {self.device_name}")

            # Ensure Bluetooth is up
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'up'],
                           check=True, capture_output=True)

            # Stop any existing advertising
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'noleadv'],
                           capture_output=True)

            # Set device name
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'name', self.device_name],
                           check=True, capture_output=True)

            # Start BLE advertising (0 = connectable undirected)
            result = subprocess.run(['sudo', 'hciconfig', 'hci0', 'leadv', '0'],
                                    capture_output=True, text=True)

            if result.returncode == 0:
                self.is_running = True
                print(f"✓ BLE advertising started: {self.device_name}")

                # Start background thread to update advertising data
                self.adv_thread = threading.Thread(target=self._update_advertising_data, daemon=True)
                self.adv_thread.start()

                return True
            else:
                print(f"✗ BLE advertising failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"✗ BLE setup error: {e}")
            return False

    def _update_advertising_data(self):
        """Background thread to update advertising data with sensor readings"""
        while self.is_running:
            try:
                # Create manufacturer data with sensor readings
                # Using a simple format: [HR high, HR low, O2%]
                manuf_data = [0x02, 0x15]  # Custom manufacturer ID
                manuf_data.extend([self.heart_rate >> 8, self.heart_rate & 0xFF])
                manuf_data.append(self.oxygen_level)

                # Convert to hex string for hcitool
                hex_data = ''.join(f'{byte:02X}' for byte in manuf_data)

                # Update advertising data (this is a simplified approach)
                # In a full implementation, you'd use proper GATT services
                cmd = [
                    'sudo', 'hcitool', 'cmd',
                    '0x08', '0x0008',  # HCI command for advertising data
                    '1E',  # Length
                    '02', '01', '06',  # Flags: LE General Discoverable
                    '03', '03', '12', '18',  # Heart Rate Service UUID
                    f'{len(self.device_name) + 1:02X}', '09'  # Complete local name
                ]

                # Add device name as ASCII bytes
                for char in self.device_name:
                    cmd.append(f'{ord(char):02X}')

                subprocess.run(cmd, capture_output=True)

            except Exception as e:
                print(f"Advertising update error: {e}")

            time.sleep(5)  # Update every 5 seconds

    def set_heart_rate(self, hr_value):
        """Update heart rate value"""
        if 30 <= hr_value <= 220:
            self.heart_rate = hr_value
            return True
        return False

    def set_oxygen_level(self, o2_value):
        """Update oxygen saturation value"""
        if 70 <= o2_value <= 100:
            self.oxygen_level = o2_value
            return True
        return False

    def stop(self):
        """Stop BLE advertising"""
        if self.is_running:
            self.is_running = False
            subprocess.run(['sudo', 'hciconfig', 'hci0', 'noleadv'],
                           capture_output=True)

            if self.adv_thread and self.adv_thread.is_alive():
                self.adv_thread.join(timeout=2)

            print("✓ BLE advertising stopped")

    def get_status(self):
        """Get current BLE status"""
        return {
            'running': self.is_running,
            'device_name': self.device_name,
            'heart_rate': self.heart_rate,
            'oxygen_level': self.oxygen_level
        }