import dbus

from advertisement import Advertisement
from service import Application, Service, Characteristic, Descriptor

GATT_CHRC_IFACE = "org.bluez.GattCharacteristic1"
NOTIFY_TIMEOUT = 5000

class SensorAdvertisment(Advertisement):
    def __init__(self,index):
        Advertisement.__init__(self,index, "peripheral")
        self.add_local_name("Sensor")
        self.include_tx_power = True

class SensorService(Service):
    SENSOR_SVC_UUID = "31c8f278-7301-4dde-b3e3-ea763aa3fdb7"

    def __init__(self, index):
        Service.__init__(self,index, self.SENSOR_SVC_UUID, True)
        self.add_characteristic(HRCharacteristic(self))
        self.add_characteristic(O2Characteristic(self))

class HRCharacteristic(Characteristic):
    HR_CHARACTERISTIC_UUID = "c1850dfb-ecee-4081-ad61-2442c5f5c341"

    def __init__(self, service):
        self.notifying = False

        Characteristic.__init__(
            self, self.HR_CHARACTERISTIC_UUID,
            ["notify", "read"], service)
        self.add_descriptor(HRDescriptor(self))

    def get_heartrate(self):
        value = []
        metric = "bpm"
        heartrate = 60

        strhr = str(heartrate) + metric
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
    HR_DESCRIPTOR_VALUE = "Heartrate"

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

        Characteristic.__init__(
            self, self.O2_CHARACTERISTIC_UUID,
            ["notify", "read"], service)
        self.add_descriptor(O2Descriptor(self))


    def get_oxygen(self):
        value = []
        metric = "%"
        oxygen = 99

        stro2 = str(oxygen) + metric
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
    O2_DESCRIPTOR_VALUE = "Oxygen"

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

app = Application()
app.add_service(SensorService(0))
app.register()

adv = SensorAdvertisment(0)
adv.register()

try:
    app.run()
except KeyboardInterrupt:
    app.quit()