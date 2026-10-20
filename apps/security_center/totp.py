"""ES: Este módulo implementa el componente totp para el dominio de seguridad.

EN: This module implements the totp component for the security center domain.

Contexto existente / Existing context:
Time-based one-time password helpers for the security center domain.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote


def generate_secret(length: int = 20) -> str:
    return base64.b32encode(secrets.token_bytes(length)).decode("ascii").rstrip("=")


def _decode_secret(secret: str) -> bytes:
    normalized = secret.strip().replace(" ", "").upper()
    padding = "=" * ((8 - len(normalized) % 8) % 8)
    return base64.b32decode(normalized + padding, casefold=True)


def code_for(secret: str, *, at_time: int | None = None, interval: int = 30, digits: int = 6) -> str:
    counter = int((at_time or int(time.time())) // interval)
    digest = hmac.new(_decode_secret(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = (struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF) % (10**digits)
    return str(number).zfill(digits)


def verify_code(secret: str, token: str, *, at_time: int | None = None, window: int = 1) -> bool:
    token = "".join(ch for ch in str(token) if ch.isdigit())
    if len(token) != 6:
        return False
    now = at_time or int(time.time())
    return any(hmac.compare_digest(code_for(secret, at_time=now + (step * 30)), token) for step in range(-window, window + 1))


def provisioning_uri(secret: str, *, account: str, issuer: str = "Vinova Pro") -> str:
    label = quote(f"{issuer}:{account}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={quote(issuer)}&algorithm=SHA1&digits=6&period=30"
