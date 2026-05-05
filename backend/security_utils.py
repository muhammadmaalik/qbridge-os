"""
Mock CRYSTALS-Kyber–style handshake primitives + HMAC request authentication.

This simulates a post-quantum KEM for session establishment; shared secrets are
then used to MAC simulation payloads (quantum-safe pipeline metaphor).
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
from typing import Tuple


def kyber512_generate_keypair() -> Tuple[str, str]:
    """Return (public_key_hex, secret_key_hex) for the mock Kyber-like KEM."""
    seed = secrets.token_bytes(32)
    sk = hashlib.sha256(seed + b"KYBER_SK").digest()
    pk = hashlib.sha256(sk + b"KYBER_PK").digest()
    return pk.hex(), sk.hex()


def kyber512_encapsulate(public_key_hex: str) -> Tuple[str, str]:
    """
    Encapsulate a shared secret against the server's public key.

    Returns:
        (ciphertext_hex, shared_secret_hex)
    """
    pk = bytes.fromhex(public_key_hex)
    shared_secret = secrets.token_bytes(32)
    pad = hashlib.sha256(pk + b"KYBER_PAD").digest()
    ct = bytes(a ^ b for a, b in zip(shared_secret, pad))
    return ct.hex(), shared_secret.hex()


def kyber512_decapsulate(secret_key_hex: str, ciphertext_hex: str) -> str:
    """Recover the shared secret from ciphertext using the server's secret key."""
    sk = bytes.fromhex(secret_key_hex)
    pk = hashlib.sha256(sk + b"KYBER_PK").digest()
    pad = hashlib.sha256(pk + b"KYBER_PAD").digest()
    ct = bytes.fromhex(ciphertext_hex)
    shared_secret = bytes(a ^ b for a, b in zip(ct, pad))
    return shared_secret.hex()


def mac_message(shared_secret_hex: str, message: str) -> str:
    """Quantum-safe request MAC (HMAC-SHA256 with Kyber-derived secret)."""
    key = bytes.fromhex(shared_secret_hex)
    msg = message.encode("utf-8")
    return hmac.new(key, msg, hashlib.sha256).hexdigest()


def verify_mac(shared_secret_hex: str, message: str, mac_hex: str) -> bool:
    expected = mac_message(shared_secret_hex, message)
    return hmac.compare_digest(expected, mac_hex)
