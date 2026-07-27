"""
AuraQA License & Hardware Protection Module
============================================
Provides two layers of protection:
  1. MASTER_KEY  — a secret passphrase stored in .env
  2. Hardware Fingerprint — a machine-specific key stored in .license

Both must be valid for the backend to start.
"""

import os
import sys
import hashlib
import hmac
import uuid
import socket
import platform
import json
from pathlib import Path

# The .license file lives next to the backend/ folder (project root)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_LICENSE_FILE = _PROJECT_ROOT / "backend" / ".license"


# ─────────────────────────────────────────────────────────────────
# Hardware Fingerprint
# ─────────────────────────────────────────────────────────────────

def get_hardware_fingerprint() -> str:
    """
    Generate a unique fingerprint for the current machine based on:
      - MAC address (network card hardware ID)
      - Machine hostname
      - Platform architecture
    Returns a SHA-256 hex digest.
    """
    try:
        mac = ':'.join([
            '{:02x}'.format((uuid.getnode() >> elements) & 0xff)
            for elements in range(0, 2 * 6, 2)
        ][::-1])
    except Exception:
        mac = "unknown-mac"

    try:
        hostname = socket.gethostname()
    except Exception:
        hostname = "unknown-host"

    try:
        arch = platform.machine()
    except Exception:
        arch = "unknown-arch"

    raw = f"{mac}|{hostname}|{arch}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ─────────────────────────────────────────────────────────────────
# License File Helpers
# ─────────────────────────────────────────────────────────────────

def generate_license_file(master_key: str) -> dict:
    """
    Generate a signed .license file for the current machine.
    The file contains:
      - hardware_hash  : fingerprint of this machine
      - signature      : HMAC-SHA256 of hardware_hash using master_key
    """
    hardware_hash = get_hardware_fingerprint()
    signature = hmac.new(
        master_key.encode("utf-8"),
        hardware_hash.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    license_data = {
        "hardware_hash": hardware_hash,
        "signature": signature,
        "system": platform.system(),
        "node": platform.node(),
    }

    with open(_LICENSE_FILE, "w") as f:
        json.dump(license_data, f, indent=2)

    return license_data


def load_license_file() -> dict:
    """Load and parse the .license file. Returns None if not found."""
    if not _LICENSE_FILE.exists():
        return None
    try:
        with open(_LICENSE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None


# ─────────────────────────────────────────────────────────────────
# Validation — called on backend startup
# ─────────────────────────────────────────────────────────────────

def validate_license(master_key: str) -> tuple[bool, str]:
    """
    Validate both the master key and hardware fingerprint.
    Returns (is_valid: bool, reason: str).
    """
    # 1. Check master key exists and is not empty
    if not master_key or master_key.strip() == "":
        return False, "MASTER_KEY is missing from .env file."

    if len(master_key) < 16:
        return False, "MASTER_KEY is too short. Minimum 16 characters required."

    # 2. Check license file exists
    license_data = load_license_file()
    if license_data is None:
        return False, (
            ".license file not found. "
            "Run 'python generate_license.py' in the backend folder first."
        )

    # 3. Check hardware fingerprint matches this machine
    current_fingerprint = get_hardware_fingerprint()
    stored_fingerprint = license_data.get("hardware_hash", "")

    if not hmac.compare_digest(current_fingerprint, stored_fingerprint):
        return False, (
            "Hardware fingerprint mismatch. "
            "This system is not licensed to run on this machine."
        )

    # 4. Verify the signature using the master key
    expected_signature = hmac.new(
        master_key.encode("utf-8"),
        stored_fingerprint.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()

    stored_signature = license_data.get("signature", "")

    if not hmac.compare_digest(expected_signature, stored_signature):
        return False, (
            "License signature invalid. "
            "The MASTER_KEY does not match the one used to generate the license."
        )

    return True, "License valid."


def enforce_license(master_key: str):
    """
    Full license enforcement. Terminates the process with a clear
    error message if the license is invalid.
    Call this once at application startup.
    """
    is_valid, reason = validate_license(master_key)
    if not is_valid:
        print("\n" + "=" * 60)
        print("  AuraQA — ACCESS DENIED")
        print("=" * 60)
        print(f"  Reason: {reason}")
        print("=" * 60 + "\n")
        sys.exit(1)
    else:
        print(f"  [AuraQA] License check passed. System authorized.")
