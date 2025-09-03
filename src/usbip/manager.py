from subprocess import run, PIPE
import os
import platform


class USBIPManager:
    def __init__(self):
        self.usbipd_running = False
        self.devices = self.get_devices()
        self.is_windows = platform.system() == "Windows"

    def start_usbipd(self):
        if not self.usbipd_running:
            if self.is_windows:
                # On Windows, use different command or skip if not applicable
                run(["usbipd", "start"], stdout=PIPE, stderr=PIPE)
            else:
                run(["sudo", "usbipd", "start"], stdout=PIPE, stderr=PIPE)
            self.usbipd_running = True

    def stop_usbipd(self):
        if self.usbipd_running:
            if self.is_windows:
                # On Windows, use different command or skip if not applicable
                run(["usbipd", "stop"], stdout=PIPE, stderr=PIPE)
            else:
                run(["sudo", "usbipd", "stop"], stdout=PIPE, stderr=PIPE)
            self.usbipd_running = False

    def get_devices(self):
        result = run(["usbip", "list", "-r", "localhost"], stdout=PIPE, stderr=PIPE)
        devices = result.stdout.decode().strip().split("\n")
        return devices

    def bind_device(self, busid):
        if self.is_windows:
            # On Windows, use different command or skip if not applicable
            run(["usbip", "bind", "-b", busid], stdout=PIPE, stderr=PIPE)
        else:
            run(["sudo", "usbip", "bind", "-b", busid], stdout=PIPE, stderr=PIPE)

    def unbind_device(self, busid):
        if self.is_windows:
            # On Windows, use different command or skip if not applicable
            run(["usbip", "unbind", "-b", busid], stdout=PIPE, stderr=PIPE)
        else:
            run(["sudo", "usbip", "unbind", "-b", busid], stdout=PIPE, stderr=PIPE)

    def add_device(self, ip_address):
        run(["usbip", "add", "-r", ip_address], stdout=PIPE, stderr=PIPE)

    def remove_device(self, ip_address):
        run(["usbip", "remove", "-r", ip_address], stdout=PIPE, stderr=PIPE)
