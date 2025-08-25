from typing import List, Dict, Any

class Device:
    def __init__(self, name: str, id: str, is_bound: bool = False):
        self.name = name
        self.id = id
        self.is_bound = is_bound

class ConnectionSettings:
    def __init__(self, ip_address: str, port: int):
        self.ip_address = ip_address
        self.port = port

class USBIPManager:
    def __init__(self):
        self.devices: List[Device] = []
        self.connection_settings: ConnectionSettings = None

    def add_device(self, device: Device):
        self.devices.append(device)

    def remove_device(self, device_id: str):
        self.devices = [device for device in self.devices if device.id != device_id]

    def toggle_device_binding(self, device_id: str):
        for device in self.devices:
            if device.id == device_id:
                device.is_bound = not device.is_bound
                break

    def set_connection_settings(self, ip_address: str, port: int):
        self.connection_settings = ConnectionSettings(ip_address, port)