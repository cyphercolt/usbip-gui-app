"""Shared subprocess runner. Uses argv lists (never a shell) and hides the console window on
Windows so running usbip/usbipd never flashes a black box.
"""

from __future__ import annotations

import platform
import subprocess
from dataclasses import dataclass

# CREATE_NO_WINDOW keeps a service/GUI from spawning visible console windows on Windows.
_CREATE_NO_WINDOW = 0x08000000 if platform.system() == "Windows" else 0


@dataclass
class CommandResult:
    ok: bool
    stdout: str
    stderr: str
    code: int


def run(argv: list[str], timeout: float = 15.0) -> CommandResult:
    try:
        proc = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
            check=False,
            creationflags=_CREATE_NO_WINDOW,
        )
        return CommandResult(proc.returncode == 0, proc.stdout, proc.stderr, proc.returncode)
    except FileNotFoundError as e:
        return CommandResult(False, "", f"command not found: {e.filename or argv[0]}", 127)
    except subprocess.TimeoutExpired:
        return CommandResult(False, "", "command timed out", 124)
