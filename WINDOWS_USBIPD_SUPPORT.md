# Windows usbipd Support

This document describes the Windows usbipd (USB/IP daemon) support in the USB/IP GUI application.

## Overview

The USB/IP GUI now supports both Linux and Windows USB/IP servers:

- **Linux systems**: Traditional `usbip` daemon with sudo requirements
- **Windows systems**: Modern `usbipd-win` service with administrator privileges

## Features

### Automatic OS Detection

When connecting via SSH, the application automatically detects:
- Remote operating system (Windows, Linux, macOS)
- Whether Windows usbipd service is available and running
- Appropriate command syntax for the detected system

### Windows usbipd Integration

For Windows systems with usbipd installed:

- **Service Management**: GUI interface to start/stop/configure the usbipd service
- **Device Listing**: Parse Windows `usbipd list` output format
- **Bind/Unbind Operations**: Use Windows `usbipd bind/unbind --busid` syntax
- **No sudo Required**: Direct command execution (administrator privileges handled by service)

### Cross-Platform Command Generation

The application automatically uses the correct commands:

| Operation | Linux | Windows (usbipd) |
|-----------|-------|------------------|
| List devices | `usbip list -l` | `usbipd list` |
| Bind device | `sudo usbip bind -b BUSID` | `usbipd bind --busid BUSID` |
| Unbind device | `sudo usbip unbind -b BUSID` | `usbipd unbind --busid BUSID` |

## Windows usbipd Service Manager

### Accessing the Service Manager

1. Connect to a Windows system via SSH
2. The "Manage usbipd Service" button will appear automatically
3. Click the button to open the service management dialog

### Service Manager Features

- **Status Monitoring**: Real-time service status display
- **Service Control**: Start/stop the usbipd service
- **Auto-Start Configuration**: Set service to start automatically
- **Installation Check**: Verify usbipd is properly installed
- **Operation Log**: View detailed service operation results

### Service Operations

#### Starting the Service
```
✅ Service started successfully
```

#### Stopping the Service
```
✅ Service stopped successfully
```

#### Setting Auto-Start
```
✅ Service set to automatic startup
```

## Installation Requirements

### Windows Systems

To use Windows usbipd support, the remote Windows system must have:

1. **usbipd-win installed**: Download from [usbipd-win releases](https://github.com/dorssel/usbipd-win/releases)
2. **SSH server enabled**: OpenSSH Server or equivalent
3. **Administrator privileges**: Required for service management and device operations

### Installation Commands (PowerShell as Administrator)

```powershell
# Install via winget (recommended)
winget install usbipd

# Or install via GitHub releases
# Download and install the .msi package from:
# https://github.com/dorssel/usbipd-win/releases
```

### Service Configuration

```powershell
# Start service manually
sc start usbipd

# Set service to start automatically
sc config usbipd start= auto

# Check service status
sc query usbipd
```

## Usage Examples

### Connecting to Windows Server

1. **Add Windows IP** to the IP management
2. **Connect via SSH** with Windows credentials
3. **OS Detection** will identify Windows and check for usbipd
4. **Service Management** button becomes available
5. **Device Operations** use Windows command syntax automatically

### Mixed Environment Support

The application seamlessly handles mixed environments:

- **Windows → Linux**: Windows client connecting to Linux server
- **Windows → Windows**: Windows client connecting to Windows server with usbipd
- **Linux → Windows**: (Future) Linux client connecting to Windows server

## Troubleshooting

### Common Issues

#### "usbipd service not available"
- **Solution**: Install usbipd-win on the remote Windows system
- **Check**: Run `usbipd --version` on remote system

#### "Access denied - administrator privileges required"
- **Solution**: Ensure SSH user has administrator privileges
- **Alternative**: Run SSH server as administrator

#### "Service failed to start"
- **Check**: Windows Event Viewer for service errors
- **Solution**: Reinstall usbipd-win or restart Windows

### Diagnostic Commands

```powershell
# Check if usbipd is installed
usbipd --version

# Check service status
sc query usbipd

# View service configuration
sc qc usbipd

# Check Windows event logs
Get-EventLog -LogName System -Source "Service Control Manager" -Message "*usbipd*"
```

## Security Considerations

### Windows Systems

- **Administrator Privileges**: Required for usbipd service operations
- **SSH Security**: Use strong passwords and consider key-based authentication
- **Firewall Rules**: Ensure USB/IP port (3240) is accessible
- **Network Security**: Use VPN or secure networks for USB/IP traffic

### Command Validation

The application validates all commands for security:
- **Bus ID Format**: Validates device identifiers
- **Command Injection**: Prevents malicious command execution
- **Input Sanitization**: Cleans all user inputs

## Advanced Configuration

### Custom usbipd Port

If using a custom port for usbipd service:

```powershell
# Stop service
sc stop usbipd

# Modify registry (example for port 3241)
reg add "HKLM\SYSTEM\CurrentControlSet\Services\usbipd\Parameters" /v Port /t REG_DWORD /d 3241

# Start service
sc start usbipd
```

### Firewall Configuration

```powershell
# Allow usbipd through Windows Firewall
netsh advfirewall firewall add rule name="USB/IP Server" dir=in action=allow protocol=TCP localport=3240
```

## Future Enhancements

Planned improvements for Windows support:

- **WinRM Integration**: Alternative to SSH for Windows management
- **PowerShell Remoting**: Native Windows remote execution
- **Service Auto-Discovery**: Automatic detection of usbipd services on network
- **Windows Event Integration**: Real-time monitoring of usbipd events
- **Multiple Service Instances**: Support for multiple usbipd services

## Compatibility Matrix

| Client OS | Server OS | USB/IP Implementation | Status |
|-----------|-----------|----------------------|--------|
| Windows | Linux | usbip daemon | ✅ Supported |
| Windows | Windows | usbipd-win service | ✅ Supported |
| Linux | Linux | usbip daemon | ✅ Supported |
| Linux | Windows | usbipd-win service | 🔄 Future |
| macOS | Linux | usbip daemon | 🔄 Future |
| macOS | Windows | usbipd-win service | 🔄 Future |
