# Linux USB/IP Service Management

## Overview
Comprehensive USB/IP daemon management for Linux systems with real-time monitoring, secure control, and intelligent status detection.

## Features

### 🔄 Real-time Service Status
- **Live daemon monitoring** with automatic status updates
- **Intelligent status detection** prioritizing actual listening ports over systemctl transitional states
- **Chronological log analysis** preventing false status reports from old log entries
- **Component breakdown** showing daemon, auto-start, modules, and command availability

### 🚀 Daemon Control
- **Start/Stop operations** with secure systemctl integration
- **Proper sudo authentication** using validated commands with password input
- **Operation timing** with appropriate delays for reliable status detection
- **Error handling** with comprehensive feedback and troubleshooting

### 🔧 Kernel Module Management
- **Load modules** - usbip_host, usbip_core, vhci_hcd
- **Unload modules** - Clean removal of USB/IP kernel components
- **Automatic loading** - Integration with daemon start operations
- **Status verification** - Real-time module status checking

### 🤖 Auto-start Configuration
- **Enable/disable** daemon auto-start on boot
- **Systemctl enable/disable** operations with proper authentication
- **Persistent configuration** surviving system reboots
- **Status indication** showing current auto-start state

## Status Indicators

### Main Status Display
- **🟢 OPERATIONAL** - Daemon is running and listening on port 3240
- **🟡 TRANSITIONING** - Daemon is starting or stopping
- **🔴 OFFLINE** - Daemon is stopped, failed, or not responding

### Component Status
- **🟢 usbipd daemon: RUNNING** - Daemon active and listening
- **🟡 usbipd daemon: STARTING** - Daemon in startup process
- **🟡 usbipd daemon: STOPPING** - Daemon shutting down
- **ℹ️ usbipd daemon: STOPPED** - Daemon not running
- **🔴 usbipd daemon: FAILED** - Daemon failed to start or crashed

- **🟢 usbipd auto-start: ENABLED** - Will start on boot
- **ℹ️ usbipd auto-start: DISABLED** - Manual start required

- **🟢 USB/IP kernel modules: LOADED** - Ready for device operations
- **🔴 USB/IP kernel modules: NOT LOADED** - Cannot attach devices

- **🟢 usbip command: AVAILABLE** - Command-line tools present
- **🔴 usbip command: NOT FOUND** - Tools not installed

## Button Controls

### Service Control
- **Start Daemon** - Enabled when daemon is stopped
- **Stop Daemon** - Enabled when daemon is running
- **Refresh Status** - Always available for manual status updates

### Auto-start Control
- **Enable Auto-start** - Configure daemon to start on boot
- **Disable Auto-start** - Prevent automatic startup

### Module Control
- **Load Modules** - Load required USB/IP kernel modules
- **Unload Modules** - Remove USB/IP kernel modules

## Technical Implementation

### Status Detection Logic
1. **Parse systemctl status output** for Active line
2. **Check chronological log entries** for listening state
3. **Prioritize listening ports** over systemctl transitional states
4. **Combine multiple indicators** for comprehensive status

### Security Features
- **Sudo command validation** using SecureCommandBuilder
- **Input sanitization** preventing command injection
- **Password handling** with secure memory management
- **Command escaping** using proper shell quoting

### Error Handling
- **Operation timeouts** preventing hanging operations
- **Detailed error messages** for troubleshooting
- **Graceful degradation** when components unavailable
- **Recovery suggestions** for common issues

## Usage Guide

### Accessing Service Management
1. Connect to a Linux SSH host
2. Click "Linux USB/IP Service" button (appears for Linux systems)
3. Enter sudo password when prompted
4. Use the service management dialog controls

### Starting the Daemon
1. Click "Start Daemon" button
2. Wait for operation to complete (3-second delay)
3. Status will update to show OPERATIONAL when ready
4. Daemon will be listening on port 3240

### Stopping the Daemon
1. Click "Stop Daemon" button
2. Wait for operation to complete (3-second delay)
3. Status will update to show OFFLINE when stopped
4. No devices can be shared until restarted

### Loading Kernel Modules
1. Click "Load Modules" button
2. Modules usbip_host, usbip_core, and vhci_hcd will be loaded
3. Required for USB/IP device operations
4. Status will show LOADED when successful

### Configuring Auto-start
1. Click "Enable Auto-start" to start daemon on boot
2. Click "Disable Auto-start" to prevent automatic startup
3. Changes take effect immediately
4. Survives system reboots

## Troubleshooting

### Common Issues

#### "Service shows as STARTING forever"
- **Cause**: Systemctl shows transitional state while daemon is actually running
- **Solution**: ✅ **FIXED** - Smart detection prioritizes listening ports

#### "Daemon status is incorrect"
- **Cause**: Old log entries showing "listening" after service stopped
- **Solution**: ✅ **FIXED** - Chronological analysis checks order of events

#### "Could not determine service status"
- **Cause**: Status checked too quickly after start/stop operations
- **Solution**: ✅ **FIXED** - Added proper delays and timing

#### "Service buttons are backwards"
- **Cause**: Button logic based on operational state instead of daemon state
- **Solution**: ✅ **FIXED** - Buttons now reflect actual daemon running status

#### "Start/Stop operations fail"
- **Cause**: Authentication or permission issues
- **Solution**: Ensure sudo access and correct password entry

#### "Kernel modules won't load"
- **Cause**: Missing kernel headers or incompatible kernel
- **Solution**: Install kernel headers: `sudo apt install linux-headers-$(uname -r)`

### Manual Commands
If GUI operations fail, try manual commands:

```bash
# Check daemon status
sudo systemctl status usbipd

# Start/stop daemon
sudo systemctl start usbipd
sudo systemctl stop usbipd

# Enable/disable auto-start
sudo systemctl enable usbipd
sudo systemctl disable usbipd

# Load/unload modules
sudo modprobe usbip_host usbip_core vhci_hcd
sudo modprobe -r usbip_host usbip_core vhci_hcd

# Check if modules are loaded
lsmod | grep -E "(usbip|vhci)"

# Check if daemon is listening
sudo netstat -tlnp | grep :3240
```

## Security Notes
- All operations use validated sudo commands
- Passwords are never stored, only used for authentication
- Command injection protection through input sanitization
- Proper shell escaping for all parameters
- Rate limiting on repeated operations
- Secure memory handling for authentication

## Integration
- Seamlessly integrates with main USB/IP GUI application
- Replaces basic "IPD Reset" functionality with comprehensive management
- Platform-aware interface (only shows for Linux SSH connections)
- Consistent with Windows usbipd service management UI
- Real-time status updates during device operations
