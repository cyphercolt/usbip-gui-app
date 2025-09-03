# IPD Reset Fix for Windows Platform

## Issue Description

When running the USB/IP GUI application on Windows and SSH'ing into a Linux system, the "IPD Reset" button was not working. This was due to platform detection changes that disabled systemctl commands on Windows, even when they were intended for remote execution on Linux systems.

## Root Cause

The `SecureCommandBuilder.build_systemctl_command()` function was checking the **local** platform (Windows) and returning `None` for systemctl commands, even when those commands were meant to be executed on a **remote** Linux system via SSH.

## Solution

### 1. Enhanced `build_systemctl_command()` Function

Added a `remote_execution` parameter to distinguish between local and remote command execution:

```python
@staticmethod
def build_systemctl_command(action: str, service: str, password: str, remote_execution: bool = False) -> Optional[str]:
    """Build a secure systemctl command
    
    Args:
        remote_execution: If True, always build the command (for SSH execution on remote Linux)
                        If False, check local platform compatibility
    """
```

### 2. Updated SSH Command Calls

Modified the `reset_usbipd()` function to use `remote_execution=True`:

```python
# For SSH execution on remote Linux system
actual_cmd = SecureCommandBuilder.build_systemctl_command("restart", "usbipd", password, remote_execution=True)
actual_status_cmd = SecureCommandBuilder.build_systemctl_command("status", "usbipd", password, remote_execution=True)
```

## Behavior After Fix

### Local Execution (Windows)
```python
# Returns None - systemctl not available locally on Windows
local_cmd = SecureCommandBuilder.build_systemctl_command("restart", "usbipd", "password", remote_execution=False)
# Result: None
```

### Remote Execution (SSH to Linux)
```python
# Returns valid command - for execution on remote Linux system
remote_cmd = SecureCommandBuilder.build_systemctl_command("restart", "usbipd", "password", remote_execution=True)
# Result: "echo password | sudo -S systemctl restart usbipd"
```

## Testing

The fix has been verified with comprehensive tests:

1. **Local Commands**: Correctly return `None` on Windows
2. **Remote Commands**: Always generate valid systemctl commands
3. **SSH Execution**: IPD Reset button now works when SSH'd into Linux systems
4. **Cross-platform**: No impact on Unix-like local systems

## Files Modified

- `src/security/validator.py`: Enhanced `build_systemctl_command()` with remote execution support
- `src/gui/window.py`: Updated `reset_usbipd()` to use remote execution parameter
- `test_windows_platform.py`: Updated tests to verify both local and remote command generation

## Usage

The IPD Reset button now works correctly:

1. **Windows → SSH → Linux**: ✅ Works (remote execution)
2. **Linux → SSH → Linux**: ✅ Works (remote execution)  
3. **Linux → Local**: ✅ Works (local execution)
4. **Windows → Local**: ❌ Disabled (systemctl not available)

This ensures the application works seamlessly across platforms while maintaining appropriate command availability based on the execution context.
