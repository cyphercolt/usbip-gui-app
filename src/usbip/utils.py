def check_usbip_installed():
    import subprocess
    try:
        result = subprocess.run(['which', 'usbip'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return result.returncode == 0
    except Exception as e:
        print(f"Error checking usbip installation: {e}")
        return False

def list_available_devices():
    import subprocess
    try:
        result = subprocess.run(['usbip', 'list', '-r', 'localhost'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        devices = result.stdout.decode('utf-8').strip().split('\n')
        return devices
    except Exception as e:
        print(f"Error listing available devices: {e}")
        return []

def connect_device(ip, bus_id):
    import subprocess
    try:
        subprocess.run(['usbip', 'bind', '-r', ip, '-b', bus_id], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error connecting device {bus_id} to {ip}: {e}")

def disconnect_device(bus_id):
    import subprocess
    try:
        subprocess.run(['usbip', 'unbind', '-b', bus_id], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error disconnecting device {bus_id}: {e}")