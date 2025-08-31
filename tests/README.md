# Tests Directory

This directory contains test files for the USB/IP GUI Application.

## Test Files

- `test_comprehensive.py` - Comprehensive test of Windows admin features and ping functionality
- `test_ipd_reset.py` - Test IPD Reset (systemctl) functionality for SSH remote execution  
- `test_usbip_client.py` - Test Windows USB/IP client functionality (attach/detach)

## Running Tests

Run tests from the root directory:

```bash
# Run all tests
python -m pytest tests/

# Run specific test
python tests/test_comprehensive.py
```

## Note

These tests may require:
- Admin privileges (Windows)
- USB/IP tools installed
- SSH access to remote servers (for some tests)
