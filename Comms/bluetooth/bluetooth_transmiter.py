import gi
from gi.repository import GLib, Gio
from pydbus import SystemBus

SERVICE_UUID = "0x180D"
CHARACTERISTICS_UUID = "0x2A37"

class ble:
    def __init__(self):
        self.bus 	 		 = SystemBus()
        self.adapter 		 = self.bus.get("org.bluez", "/org/bluez/hci0")
        self.service_manager = self.bus.get("org.bluez", "/org/bluez/hci0")
        
        self.service = {
            "UUID": SERVICE_UUID,
            "Primary": True,
            "Characteristics": [
                
                {
                    "UUID": CHARACTERISTICS_UUID,
                    "Flags": ["read", "notify"],
                    "Value": [0x42]
                }   
            ]
        }
        
    def register_service(self):
        print("RegGATT")
        service_path = "/org/bluez/example/service"
        s_var = GLib.Variant("s", service_path)
        c_var = GLib.Variant("a{sv}", self.service)
        self.service_manager.RegisterApplication(s_var, c_var)

if __name__ == "__main__":
    peripheral = ble()
    peripheral.register_service()
    Glib.MainLoop().run()
        
        