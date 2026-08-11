"""usbip-node: one symmetric LAN service = agent + hub + webserver for USB/IP fleet control.

Every machine runs an identical copy. Connect Android Chrome to any node's IP and you get the same
aggregated fleet view; nodes discover each other over mDNS and orchestrate any-PC -> any-PC attach.
"""

__version__ = "0.1.1b"
