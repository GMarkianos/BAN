#!/usr/bin/python3
# ble_sensor_lib.py - BLE Sensor Library

import dbus
import dbus.mainloop.glib

try:
    from gi.repository import GObject
except ImportError:
    import gobject as GObject

# Bluetooth constants
BLUEZ_SERVICE_NAME = "org.bluez"
GATT_MANAGER_IFACE = "org.bluez.GattManager1"
LE_ADVERTISING_MANAGER_IFACE = "org.bluez.LEAdvertisingManager1"
DBUS_OM_IFACE = "org.freedesktop.DBus.ObjectManager"
DBUS_PROP_IFACE = "org.freedesktop.DBus.Properties"
GATT_SERVICE_IFACE = "org.bluez.GattService1"
GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
LE_ADVERTISEMENT_IFACE = "org.bluez.LEAdvertisement1"


class BLESensorManager:
    """
    Main BLE Sensor Manager - Provides a clean interface for HR/O2 sensor advertising
    """

    def __init__(self, device_name="Sensor"):
        self.device_name = device_name
        self.app = None
        self.adv = None
        self.is_running = False

        # Sensor data storage
        self.heart_rate = 72
        self.oxygen_level = 98
        self.callbacks = {
            'on_start': None,
            'on_stop': None,
            'on_error': None
        }

    def set_heart_rate(self, hr_value):
        """Update heart rate value"""
        if 30 <= hr_value <= 220:  # Reasonable HR range
            self.heart_rate = hr_value
            return True
        return False

    def set_oxygen_level(self, o2_value):
        """Update oxygen saturation value"""
        if 70 <= o2_value <= 100:  # Reasonable O2 range
            self.oxygen_level = o2_value
            return True
        return False

    def set_callbacks(self, on_start=None, on_stop=None, on_error=None):
        """Set callback functions for events"""
        self.callbacks['on_start'] = on_start
        self.callbacks['on_stop'] = on_stop
        self.callbacks['on_error'] = on_error

    def _execute_callback(self, callback_name, *args):
        """Helper to execute callbacks safely"""
        callback = self.callbacks.get(callback_name)
        if callback:
            try:
                callback(*args)
            except Exception as e:
                print(f"Callback error: {e}")

    def start_advertising(self):
        """Start BLE advertising with HR and O2 services"""
        try:
            dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

            self.app = _SensorApplication(self)
            self.app.register()

            self.adv = _SensorAdvertisement(0, self.device_name)
            self.adv.register()

            self.is_running = True
            self._execute_callback('on_start')
            print(f"BLE Sensor '{self.device_name}' started successfully")
            return True

        except Exception as e:
            self._execute_callback('on_error', str(e))
            print(f"Failed to start BLE: {e}")
            return False

    def run(self):
        """Run the main loop (blocking)"""
        if self.app and self.is_running:
            try:
                self.app.run()
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """Stop BLE advertising"""
        if self.app and self.is_running:
            self.app.quit()
            self.is_running = False
            self._execute_callback('on_stop')
            print("BLE Sensor stopped")

    def get_status(self):
        """Get current status"""
        return {
            'running': self.is_running,
            'device_name': self.device_name,
            'heart_rate': self.heart_rate,
            'oxygen_level': self.oxygen_level
        }


# Internal implementation classes (not part of public API)
class _SensorAdvertisement(dbus.service.Object):
    PATH_BASE = "/org/bluez/example/advertisement"

    def __init__(self, index, device_name):
        self.path = self.PATH_BASE + str(index)
        self.bus = dbus.SystemBus()
        self.ad_type = "peripheral"
        self.local_name = device_name
        self.include_tx_power = True
        dbus.service.Object.__init__(self, self.bus, self.path)

    def get_properties(self):
        return {
            LE_ADVERTISEMENT_IFACE: {
                "Type": self.ad_type,
                "LocalName": dbus.String(self.local_name),
                "IncludeTxPower": dbus.Boolean(self.include_tx_power),
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_PROP_IFACE, in_signature="s", out_signature="a{sv}")
    def GetAll(self, interface):
        if interface != LE_ADVERTISEMENT_IFACE:
            raise Exception("Invalid interface")
        return self.get_properties()[LE_ADVERTISEMENT_IFACE]

    @dbus.service.method(LE_ADVERTISEMENT_IFACE, in_signature='', out_signature='')
    def Release(self):
        pass

    def register(self):
        adapter = self._find_adapter()
        ad_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            LE_ADVERTISING_MANAGER_IFACE
        )
        ad_manager.RegisterAdvertisement(
            self.get_path(), {},
            reply_handler=lambda: print("Advertisement registered"),
            error_handler=lambda e: print(f"Advertisement error: {e}")
        )

    def _find_adapter(self):
        remote_om = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, "/"),
            DBUS_OM_IFACE
        )
        objects = remote_om.GetManagedObjects()
        for o, props in objects.items():
            if LE_ADVERTISING_MANAGER_IFACE in props:
                return o
        return None


class _SensorApplication(dbus.service.Object):
    def __init__(self, manager):
        self.manager = manager
        self.bus = dbus.SystemBus()
        self.path = "/"
        self.services = []
        self.mainloop = GObject.MainLoop()
        dbus.service.Object.__init__(self, self.bus, self.path)

        # Add sensor service
        self.services.append(_SensorService(0, manager))

    def get_path(self):
        return dbus.ObjectPath(self.path)

    @dbus.service.method(DBUS_OM_IFACE, out_signature="a{oa{sa{sv}}}")
    def GetManagedObjects(self):
        response = {}
        for service in self.services:
            response[service.get_path()] = service.get_properties()
            for chrc in service.get_characteristics():
                response[chrc.get_path()] = chrc.get_properties()
        return response

    def register(self):
        adapter = self._find_adapter()
        service_manager = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, adapter),
            GATT_MANAGER_IFACE
        )
        service_manager.RegisterApplication(
            self.get_path(), {},
            reply_handler=lambda: print("GATT application registered"),
            error_handler=lambda e: print(f"GATT registration error: {e}")
        )

    def run(self):
        self.mainloop.run()

    def quit(self):
        self.mainloop.quit()

    def _find_adapter(self):
        remote_om = dbus.Interface(
            self.bus.get_object(BLUEZ_SERVICE_NAME, "/"),
            DBUS_OM_IFACE
        )
        objects = remote_om.GetManagedObjects()
        for o, props in objects.items():
            if LE_ADVERTISING_MANAGER_IFACE in props:
                return o
        return None


class _SensorService(dbus.service.Object):
    SENSOR_SVC_UUID = "31c8f278-7301-4dde-b3e3-ea763aa3fdb7"

    def __init__(self, index, manager):
        self.path = f"/org/bluez/example/service{index}"
        self.bus = dbus.SystemBus()
        self.manager = manager
        self.characteristics = []
        dbus.service.Object.__init__(self, self.bus, self.path)

        # Add characteristics
        self.characteristics.append(_HRCharacteristic(self, manager))
        self.characteristics.append(_O2Characteristic(self, manager))

    def get_properties(self):
        return {
            GATT_SERVICE_IFACE: {
                'UUID': self.SENSOR_SVC_UUID,
                'Primary': True,
                'Characteristics': dbus.Array(
                    [chrc.get_path() for chrc in self.characteristics],
                    signature='o'
                )
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_characteristics(self):
        return self.characteristics

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_SERVICE_IFACE:
            raise Exception("Invalid interface")
        return self.get_properties()[GATT_SERVICE_IFACE]


class _HRCharacteristic(dbus.service.Object):
    HR_CHARACTERISTIC_UUID = "c1850dfb-ecee-4081-ad61-2442c5f5c341"

    def __init__(self, service, manager):
        self.path = service.path + '/char0'
        self.bus = service.bus
        self.service = service
        self.manager = manager
        self.notifying = False
        dbus.service.Object.__init__(self, self.bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.HR_CHARACTERISTIC_UUID,
                'Flags': ['notify', 'read'],
                'Descriptors': dbus.Array([], signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_heartrate(self):
        hr = self.manager.heart_rate
        return [dbus.Byte(c.encode()) for c in f"{hr} bpm"]

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise Exception("Invalid interface")
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        return self.get_heartrate()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False


class _O2Characteristic(dbus.service.Object):
    O2_CHARACTERISTIC_UUID = "95f75eed-bb38-423c-b67b-e2d3c16e0c3e"

    def __init__(self, service, manager):
        self.path = service.path + '/char1'
        self.bus = service.bus
        self.service = service
        self.manager = manager
        self.notifying = False
        dbus.service.Object.__init__(self, self.bus, self.path)

    def get_properties(self):
        return {
            GATT_CHRC_IFACE: {
                'Service': self.service.get_path(),
                'UUID': self.O2_CHARACTERISTIC_UUID,
                'Flags': ['notify', 'read'],
                'Descriptors': dbus.Array([], signature='o')
            }
        }

    def get_path(self):
        return dbus.ObjectPath(self.path)

    def get_oxygen(self):
        o2 = self.manager.oxygen_level
        return [dbus.Byte(c.encode()) for c in f"{o2}%"]

    @dbus.service.method(DBUS_PROP_IFACE, in_signature='s', out_signature='a{sv}')
    def GetAll(self, interface):
        if interface != GATT_CHRC_IFACE:
            raise Exception("Invalid interface")
        return self.get_properties()[GATT_CHRC_IFACE]

    @dbus.service.method(GATT_CHRC_IFACE, in_signature='a{sv}', out_signature='ay')
    def ReadValue(self, options):
        return self.get_oxygen()

    @dbus.service.method(GATT_CHRC_IFACE)
    def StartNotify(self):
        self.notifying = True

    @dbus.service.method(GATT_CHRC_IFACE)
    def StopNotify(self):
        self.notifying = False