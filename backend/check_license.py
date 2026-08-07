"""
AuraQA - License Validation Check
===================================
Called by run_servers.bat at startup.
Returns exit code 0 if license is valid, 1 if invalid or missing.
"""
import sys
import json
import hashlib
import hmac as hmac_module
import uuid
import socket
import platform
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    BACKEND_DIR = Path(__file__).resolve().parent
    load_dotenv(BACKEND_DIR / ".env")

    master_key = os.getenv("MASTER_KEY", "").strip()
    if not master_key or len(master_key) < 16:
        sys.exit(1)

    license_file = BACKEND_DIR / ".license"
    if not license_file.exists():
        sys.exit(1)

    with open(license_file, "r") as f:
        data = json.load(f)

    mac = ':'.join([
        '{:02x}'.format((uuid.getnode() >> e) & 0xff)
        for e in range(0, 12, 2)
    ][::-1])
    hw = hashlib.sha256(
        (mac + "|" + socket.gethostname() + "|" + platform.machine()).encode()
    ).hexdigest()

    if not hmac_module.compare_digest(hw, data.get("hardware_hash", "")):
        sys.exit(1)

    expected_sig = hmac_module.new(
        master_key.encode(),
        data["hardware_hash"].encode(),
        hashlib.sha256
    ).hexdigest()

    if not hmac_module.compare_digest(expected_sig, data.get("signature", "")):
        sys.exit(1)

    sys.exit(0)

except Exception:
    sys.exit(1)
