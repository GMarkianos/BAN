import dbus
import time

from Comms.bluetooth.advertisement import Advertisement
from Comms.bluetooth.service import Application, Service, Characteristic, Descriptor

GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
NOTIFY_TIMEOUT = 5000

class SensorAdvertisement(Advertisement):
    def __init__(self, index):
        Advertisement.__init__(self, index, "peripheral")
        self.add_local_name("HealthSensor")
        self.include_tx_power = True
        print("✓ SensorAdvertisement created")


class SensorService(Service):
    SENSOR_SVC_UUID = "31c8f278-7301-4dde-b3e3-ea763aa3fdb7"

    def __init__(self, index):
        Service.__init__(self, index, self.SENSOR_SVC_UUID, True)

        # Create characteristics and store references
        self.hr_characteristic = HRCharacteristic(self)
        self.o2_characteristic = O2Characteristic(self)

        # Add to service
        self.add_characteristic(self.hr_characteristic)
        self.add_characteristic(self.o2_characteristic)

class HRCharacteristic(Characteristic):
    HR_CHARACTERISTIC_UUID = "c1850dfb-ecee-4081-ad61-2442c5f5c341"

    def __init__(self, service):
        self.notifying = False
        self.heart_rate = 0

        Characteristic.__init__(
            self, self.HR_CHARACTERISTIC_UUID,
            ["read", "notify"], service)
        self.add_descriptor(HRDescriptor(self))

    def set_heart_rate(self, hr_value):
        """Update heart rate value - no validation"""
        self.heart_rate = hr_value
        # Notify connected clients of the change
        if self.notifying:
            value = self.get_heartrate()
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        return True

    def get_heartrate(self):
        """Return heart rate as string bytes (simpler approach)"""
        value = []
        hr_str = str(self.heart_rate)
        for char in hr_str:
            value.append(dbus.Byte(char.encode()))
        return value

    def set_heartrate_callback(self):
        if self.notifying:
            value = self.get_heartrate()
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

        value = self.get_heartrate()
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.set_heartrate_callback)

    def StopNotify(self):
        self.notifying = False

    def ReadValue(self, options):
        """This is called when a client reads the characteristic"""
        return self.get_heartrate()

class HRDescriptor(Descriptor):
    HR_DESCRIPTOR_UUID = "2901"
    HR_DESCRIPTOR_VALUE = "Heart Rate (bpm)"

    def __init__(self, characteristic):
        Descriptor.__init__(
            self, self.HR_DESCRIPTOR_UUID,
            ["read"],
            characteristic)

    def ReadValue(self, options):
        value = []
        desc = self.HR_DESCRIPTOR_VALUE
        for c in desc:
            value.append(dbus.Byte(c.encode()))
        return value

class O2Characteristic(Characteristic):
    O2_CHARACTERISTIC_UUID = "95f75eed-bb38-423c-b67b-e2d3c16e0c3e"

    def __init__(self, service):
        self.notifying = False
        self.oxygen_level = 0

        Characteristic.__init__(
            self, self.O2_CHARACTERISTIC_UUID,
            ["read", "notify"], service)
        self.add_descriptor(O2Descriptor(self))

    def set_oxygen_level(self, o2_value):
        """Update oxygen level value - no validation"""
        self.oxygen_level = o2_value
        # Notify connected clients of the change
        if self.notifying:
            value = self.get_oxygen()
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        return True

    def get_oxygen(self):
        """Return oxygen level as string bytes (simpler approach)"""
        value = []
        o2_str = str(self.oxygen_level)
        for char in o2_str:
            value.append(dbus.Byte(char.encode()))
        return value

    def set_oxygen_callback(self):
        if self.notifying:
            value = self.get_oxygen()
            self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        return self.notifying

    def StartNotify(self):
        if self.notifying:
            return
        self.notifying = True

        value = self.get_oxygen()
        self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
        self.add_timeout(NOTIFY_TIMEOUT, self.set_oxygen_callback)

    def StopNotify(self):
        self.notifying = False


    def ReadValue(self, options):
        """This is called when a client reads the characteristic"""
        return self.get_oxygen()

class O2Descriptor(Descriptor):
    O2_DESCRIPTOR_UUID = "2901"
    O2_DESCRIPTOR_VALUE = "Oxygen Saturation (%)"

    def __init__(self, characteristic):
        Descriptor.__init__(
            self, self.O2_DESCRIPTOR_UUID,
            ["read"],
            characteristic)

    def ReadValue(self, options):
        value = []
        desc = self.O2_DESCRIPTOR_VALUE
        for c in desc:
            value.append(dbus.Byte(c.encode()))
        return value

# Remove the standalone application code since we're integrating with main.py