"""Web-UI login: a username/password (optionally + TOTP 2FA) that gates the browser-facing API so
people on the LAN can't drive USB without the credential.

The credential is set once and synced to every paired machine (see routes /api/auth/sync and the
push-on-pair), so the same login works on any node's web UI. Hashing is PBKDF2-HMAC-SHA256 and TOTP
is RFC 6238 — both stdlib, no extra deps. Sessions are in-memory bearer tokens in a cookie.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import struct
import threading
import time
from pathlib import Path

from .config import state_dir

_ITERS = 200_000
COOKIE = "usbip_session"


def _hash(password: str, salt: bytes) -> str:
    return base64.b64encode(hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERS)).decode()


def totp_code(secret_b32: str, at: float | None = None, step: int = 30, digits: int = 6) -> str:
    key = base64.b32decode(secret_b32, casefold=True)
    counter = int((at if at is not None else time.time()) // step)
    mac = hmac.new(key, struct.pack(">Q", counter), hashlib.sha1).digest()
    off = mac[-1] & 0x0F
    code = (struct.unpack(">I", mac[off : off + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)


def totp_valid(secret_b32: str, code: str) -> bool:
    if not code:
        return False
    now = time.time()
    return any(hmac.compare_digest(totp_code(secret_b32, now + w * 30), code) for w in (-1, 0, 1))


class WebAuthStore:
    def __init__(self, path: Path | None = None) -> None:
        self._path = path or (state_dir() / "webauth.json")
        self._lock = threading.Lock()
        self._data = self._load()
        self._sessions: set[str] = set()

    def _load(self) -> dict:
        try:
            return json.loads(self._path.read_text())
        except (OSError, json.JSONDecodeError):
            return {"enabled": False}

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._data))
        except OSError:
            pass

    # ---- state ----
    def enabled(self) -> bool:
        return bool(self._data.get("enabled"))

    def totp_enabled(self) -> bool:
        return bool(self._data.get("totp_secret"))

    def username(self) -> str:
        return self._data.get("username", "")

    # ---- credential management ----
    def set_credential(self, username: str, password: str, totp_enabled: bool) -> str | None:
        """Set/replace the login. Returns the TOTP secret if 2FA is being enabled (to show once)."""
        salt = secrets.token_bytes(16)
        with self._lock:
            self._data = {
                "enabled": True,
                "username": username,
                "salt": base64.b64encode(salt).decode(),
                "hash": _hash(password, salt),
            }
            secret = None
            if totp_enabled:
                secret = base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")
                self._data["totp_secret"] = secret
            self._save()
            return secret

    def disable(self) -> None:
        with self._lock:
            self._data = {"enabled": False}
            self._save()
            self._sessions.clear()

    def verify(self, username: str, password: str, code: str | None) -> bool:
        if not self.enabled():
            return True
        d = self._data
        if username != d.get("username"):
            return False
        salt = base64.b64decode(d["salt"])
        if not hmac.compare_digest(_hash(password, salt), d["hash"]):
            return False
        if d.get("totp_secret"):
            return totp_valid(d["totp_secret"], code or "")
        return True

    # ---- sync across paired peers ----
    def export_config(self) -> dict:
        return dict(self._data)

    def import_config(self, cfg: dict) -> None:
        with self._lock:
            self._data = dict(cfg)
            self._save()
            self._sessions.clear()  # credential changed; force re-login

    # ---- sessions ----
    def create_session(self) -> str:
        token = secrets.token_urlsafe(32)
        with self._lock:
            self._sessions.add(token)
        return token

    def valid_session(self, token: str | None) -> bool:
        return bool(token) and token in self._sessions

    def drop_session(self, token: str | None) -> None:
        if token:
            self._sessions.discard(token)
