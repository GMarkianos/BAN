import sys
import atexit
import time
import threading
from Comms.bluetooth.service import Application
from Comms.bluetooth.sensor import SensorService, SensorAdvertisement


class BLEAgent:
    """BLE Agent for handling Bluetooth Low Energy communication"""

    def __init__(self):
        self._ble_app = None
        self._ble_hr_characteristic = None
        self._ble_o2_characteristic = None
        self._ble_thread = None
        self._ble_running = False
        self._ble_advertisement = None
        self._initialized = False

        # Register cleanup handler only
        atexit.register(self.cleanup)

    def start(self):
        """Start BLE service"""
        try:
            print("🔄 Initializing BLE service...")

            # Create BLE application
            self._ble_app = Application()

            # Create sensor service
            sensor_service = SensorService(0)

            # Store references to characteristics BEFORE adding to app
            self._ble_hr_characteristic = None
            self._ble_o2_characteristic = None

            for characteristic in sensor_service.characteristics:
                if hasattr(characteristic, 'HR_CHARACTERISTIC_UUID'):
                    self._ble_hr_characteristic = characteristic
                    print("✓ Found HR characteristic")
                elif hasattr(characteristic, 'O2_CHARACTERISTIC_UUID'):
                    self._ble_o2_characteristic = characteristic
                    print("✓ Found O2 characteristic")

            # Add service to application
            self._ble_app.add_service(sensor_service)

            # Register BLE application
            self._ble_app.register()
            print("✓ GATT application registered")

            # Wait a moment before registering advertisement (critical timing!)
            time.sleep(0.5)

            # CREATE AND REGISTER ADVERTISEMENT
            self._ble_advertisement = SensorAdvertisement(0)
            self._ble_advertisement.register()
            print("✓ BLE advertisement registered")

            # Start BLE in background thread
            self._ble_running = True
            self._ble_thread = threading.Thread(target=self._run_ble, daemon=True)
            self._ble_thread.start()

            self._initialized = True
            print("✓ BLE service started successfully")
            print("📱 Device should now appear as 'HealthSensor' in nRF Connect")
            time.sleep(3)
            return True

        except Exception as e:
            print(f"✗ Failed to start BLE service: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _run_ble(self):
        """Run BLE mainloop in separate thread"""
        try:
            self._ble_app.run()
        except Exception as e:
            print(f"BLE thread error: {e}")
        finally:
            self._ble_running = False

    def update_data(self, heart_rate, oxygen_level):
        """Update BLE characteristics with current sensor data - always send"""
        if not self._initialized:
            return

        try:
            if self._ble_hr_characteristic:
                self._ble_hr_characteristic.set_heart_rate(heart_rate)

            if self._ble_o2_characteristic:
                self._ble_o2_characteristic.set_oxygen_level(oxygen_level)

            print(f"📡 BLE Updated - HR: {heart_rate}, O2: {oxygen_level}")

        except Exception as e:
            print(f"⚠ BLE data update error: {e}")

    def is_running(self):
        """Check if BLE agent is initialized and running"""
        return self._initialized and self._ble_running

    def cleanup(self):
        """Properly shutdown BLE service"""
        if not self._initialized:
            return

        print("🛑 Cleaning up BLE agent...")

        # Stop BLE service
        if self._ble_app:
            print("Stopping BLE service...")
            self._ble_app.quit()
            self._ble_running = False

        # Stop BLE advertisement
        if self._ble_advertisement:
            print("Stopping BLE advertisement...")
            try:
                from Comms.bluetooth.bletools import BleTools
                import dbus
                bus = BleTools.get_bus()
                adapter = BleTools.find_adapter(bus)
                ad_manager = dbus.Interface(
                    bus.get_object("org.bluez", adapter),
                    "org.bluez.LEAdvertisingManager1"
                )
                ad_manager.UnregisterAdvertisement(self._ble_advertisement.get_path())
            except:
                pass  # Ignore errors during cleanup

        self._initialized = False
        print("✓ BLE cleanup complete")

    def stop(self):
        """Stop BLE without atexit cleanup"""
        self.cleanup()
