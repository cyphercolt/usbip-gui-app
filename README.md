# USBIP GUI Application

A modern Linux desktop GUI for managing USBIP devices locally and remotely via SSH.

## Features

- Attach/detach USB devices from remote servers using USBIP.
- Bind/unbind USB devices on remote servers via SSH.
- View and manage local and remote USB devices in separate tables.
- SSH credential remembering (username & fingerprint acceptance per IP).
- Restart and check status of `usbipd` service on remote servers.
- Console output for all commands and errors.

## Requirements

- Python 3.8+
- Linux (tested on Ubuntu/Pop!_OS)
- **usbip** system package (`sudo apt install usbip` on Ubuntu/Debian)
- USBIP installed and configured on local and remote systems
- `usbipd` running on remote servers
- Sudo access for USBIP commands
- SSH access to remote servers

## Project Structure

```
usbip-gui-app
├── src
│   ├── main.py               # Entry point of the application
│   ├── gui
│   │   └── window.py         # Main GUI window class
│   ├── usbip
│   │   ├── manager.py        # USBIP management logic
│   │   └── utils.py          # Utility functions for USBIP
│   ├── dependencies
│   │   └── checker.py        # Dependency checker
│   └── types
│       └── index.py          # Custom types and data structures
├── requirements.txt          # Python package dependencies
└── README.md                 # Project documentation
```

## Installation

```sh
git clone https://github.com/cyphercolt/usbip-gui-app.git
cd usbip-gui-app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Usage

```sh
python3 src/main.py
```

- Add IPs/hostnames of remote servers.
- Click "SSH Devices" to connect and manage remote USB devices.
- Use "Attach" and "Bind" checkboxes to control devices.
- Use "IPD Reset" to restart the remote usbipd service.

## Security Notes

- SSH passwords and sudo passwords are never stored.
- Only SSH username and fingerprint acceptance are remembered per IP.
- Use on trusted networks and systems.

## Credits

This project was vibe-coded with the help of [GitHub Copilot](https://github.com/features/copilot)  
and thoroughly tested by real humans for usability and reliability.

## License

MIT License (see LICENSE file)