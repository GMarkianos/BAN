from bluepy.btle import Peripheral, Characteristic, Service, UUID, BTLEException

class SensorPeripheral(Peripheral):
    def __init__(self):
        Peripheral.__init__(self)
        self.svc = self.addService(Service(UUID(0x180D)))
        self.chr = self.svc.addCharacteristic(UUID(0x2A37), Characteristic.PROPERTY_READ | Characteristic.PROPERTY_NOTIFY, Characteristic.PERMISSION_READ)
        self.setCallbacks()

    def setCallbacks(self):
        self.chr.setCallbacks(CharacteristicCallbacks())
        
class CharacteristicCallbacks(Characteristic.Characteristic):
    def onReadRequest(self, handle, offset):
        return self.getSensorData()

    def getSensorData(self):
        # Replace this with your sensor data retrieval logic
        return "Sensor Data"

if __name__ == "__main__":
    sensor = SensorPeripheral()
    try:
        sensor.advertise("Sensor")
        while True:
            pass
    except KeyboardInterrupt:
        sensor.disconnect()
