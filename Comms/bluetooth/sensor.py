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
        self.heart_rate = 72  # Default value

        Characteristic.__init__(
            self, self.HR_CHARACTERISTIC_UUID,
            ["notify", "read"], service)
        self.add_descriptor(HRDescriptor(self))

    def set_heart_rate(self, hr_value):
        """Update heart rate value"""
        # Allow wider range for testing, including -1 for debugging
        if -1 <= hr_value <= 250:  # Expanded range for testing
            self.heart_rate = hr_value
            # Notify subscribers if notifications are enabled
            if self.notifying:
                value = self.get_heartrate()
                self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
            return True
        print(f"⚠ HR value {hr_value} out of range")
        return False

    def get_heartrate(self):
        value = []
        strhr = str(self.heart_rate)
        for c in strhr:
            value.append(dbus.Byte(c.encode()))
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
        value = self.get_heartrate()
        return value

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
        self.oxygen_level = 98  # Default value

        Characteristic.__init__(
            self, self.O2_CHARACTERISTIC_UUID,
            ["notify", "read"], service)
        self.add_descriptor(O2Descriptor(self))

    def set_oxygen_level(self, o2_value):
        """Update oxygen level value"""
        # Allow wider range for testing, including -1 for debugging
        if -1 <= o2_value <= 100:  # Allow -1 for debugging
            self.oxygen_level = o2_value
            # Notify subscribers if notifications are enabled
            if self.notifying:
                value = self.get_oxygen()
                self.PropertiesChanged(GATT_CHRC_IFACE, {"Value": value}, [])
            return True
        print(f"⚠ O2 value {o2_value} out of range")
        return False

    def get_oxygen(self):
        value = []
        stro2 = str(self.oxygen_level)
        for c in stro2:
            value.append(dbus.Byte(c.encode()))
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
        value = self.get_oxygen()
        return value

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