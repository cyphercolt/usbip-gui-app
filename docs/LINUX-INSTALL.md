# USB/IP GUI App - Linux Installation Guide

## Quick Start

1. **Download the executable**: `USB-IP-GUI` from the `dist/` folder
2. **Make it executable**: `chmod +x USB-IP-GUI`
3. **Run it**: `./USB-IP-GUI`

## Prerequisites

Before running the USB/IP GUI App, make sure you have the required system packages installed:

### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install usbip hwdata usbutils
```

### Fedora/RHEL/CentOS:
```bash
sudo dnf install usbip usbutils
# or for older versions:
sudo yum install usbip usbutils
```

### Arch Linux:
```bash
sudo pacman -S usbip usbutils
```

## Running the Application

1. **Make the executable file executable** (if not already):
   ```bash
   chmod +x USB-IP-GUI
   ```

2. **Run the application**:
   ```bash
   ./USB-IP-GUI
   ```

3. **For system-wide installation** (optional):
   ```bash
   sudo cp USB-IP-GUI /usr/local/bin/
   sudo chmod +x /usr/local/bin/USB-IP-GUI
   ```
   Then you can run it from anywhere with: `USB-IP-GUI`

## Important Notes

- **Sudo privileges**: The application requires sudo access for USB operations
- **Network access**: Make sure you can reach the remote USB/IP server
- **Firewall**: USB/IP typically uses port 3240 (TCP)
- **Dependencies**: All Python dependencies are bundled in the executable

## Troubleshooting

### "usbip command not found"
Install the usbip package for your distribution (see Prerequisites above).

### Permission errors
Make sure your user has sudo privileges, or run the app with sudo:
```bash
sudo ./USB-IP-GUI
```

### Network connection issues
- Check if the remote server is running USB/IP daemon
- Verify firewall settings allow port 3240
- Test connectivity: `telnet <server-ip> 3240`

## Features

- ✅ Cross-platform support (Linux ↔ Windows USB/IP)
- ✅ Device binding/unbinding on remote servers
- ✅ Device attachment/detachment locally
- ✅ Auto-reconnection for persistent setups
- ✅ Encrypted credential storage
- ✅ Real-time device state monitoring

## Support

For issues or questions, check the project repository or documentation.
