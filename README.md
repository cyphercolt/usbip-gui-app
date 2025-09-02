# 🖥️ USBIP GUI Application

A **secure**, cross-platform desktop GUI for managing USBIP devices locally and remotely via SSH. Perfect for gaming setups, home labs, and remote USB device management. Runs on **Linux** and **Windows**.

**Note**: Fully coded with GitHub Copilot. I needed a USB-over-IP app tailored to my needs, and I'm not a coder, so here we are!

## ✨ Features

- 🔌 **Device Management** - Attach/detach USB devices with auto-reconnect
- 🔒 **Military-Grade Security** - AES-256 encryption, memory protection  
- 🎨 **Modern UI** - 4 themes with complete persistence
- 🎮 **Gaming Optimized** - Real-time ping monitoring
- 🚀 **Smart Automation** - Auto-reconnect, bulk operations
- 🛡️ **SSH Integration** - Secure remote device management

## 📸 Screenshots
<img width="402" height="230" alt="image" src="https://github.com/user-attachments/assets/d1a8f619-e839-4258-ab44-a5de04e2ea1f" /> <img width="249" height="181" alt="image" src="https://github.com/user-attachments/assets/dab0290b-6e21-4e83-a4ed-0a5b631b574b" />
<img width="1455" height="933" alt="image" src="https://github.com/user-attachments/assets/aa69553a-b549-4c4b-97bd-50083c746377" />

## 🚀 Installation

### Linux
```bash
git clone https://github.com/cyphercolt/usbip-gui-app.git
cd usbip-gui-app
sudo apt install usbip
sudo modprobe vhci_hcd usbip_host
echo -e "vhci_hcd\nusbip_host" | sudo tee /etc/modules-load.d/usbip.conf
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 src/main.py
```

### Windows
```powershell
git clone https://github.com/cyphercolt/usbip-gui-app.git
cd usbip-gui-app
# Install Windows USB/IP from Microsoft: https://github.com/dorssel/usbipd-win
winget install usbipd
# Also install usbip-win2 for client functionality: https://github.com/vadimgrn/usbip-win2
# Download and install usbip-win2 from the releases page
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python src/main.py
```

## 🔧 Usage

1. Add IP addresses via "Manage IPs"
2. Select IP from dropdown (auto-pings)
3. Connect via SSH to load remote devices
4. Bind/Unbind devices on remote server
5. Attach/Detach devices locally
6. Enable Auto-reconnect for critical devices

## 🎯 Use Cases

- Gaming controllers with auto-reconnect
- Development hardware sharing
- Home lab USB management
- Remote workstation peripherals

## 🔒 Security

- AES-256 encryption with machine-specific keys
- Memory protection with automatic cleanup
- Rate limiting and brute force protection
- No plaintext credential storage

## 🔧 Troubleshooting

### Linux
```bash
# Kernel modules not loaded
sudo modprobe vhci_hcd usbip_host

# Check service status
sudo systemctl status usbipd
```

### Windows
```powershell
# Check usbipd service
usbipd list

# Restart service if needed
Restart-Service usbipd
```

## 🤝 Contributing

Contributions welcome! Maintain security standards and Qt patterns.

## 📜 License

MIT License - See LICENSE file for details.

---

**⭐ 7,729 lines of secure Python code built with AI**
