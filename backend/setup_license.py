"""
AuraQA - License Setup from Provided Key
=========================================
Called by key_prompt.py after user enters a key.
Takes the key as a command-line argument, generates a
.license for this machine, and writes/updates .env.

Exit codes:
  0 = success (key is valid, license created)
  1 = failure (key is wrong or too short)
"""

import sys
import hashlib
import hmac as hmac_module
import uuid
import socket
import platform
import json
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
LICENSE_FILE = BACKEND_DIR / ".license"
ENV_FILE = BACKEND_DIR / ".env"

# Default .env values for a fresh installation
DEFAULT_ENV = """DATABASE_URL=sqlite:///./chatbot.db
JWT_SECRET_KEY=9ad0bdc4a48f4f06b72bcf3e4c01e215d389cd8172cd4b1f92e1b891df37a64
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
ALLOWED_ORIGINS=http://localhost:5000,http://127.0.0.1:5000
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen2.5:0.5b
SIMILARITY_THRESHOLD=0.40
"""


def get_hardware_fingerprint() -> str:
    try:
        mac = ':'.join([
            '{:02x}'.format((uuid.getnode() >> e) & 0xff)
            for e in range(0, 12, 2)
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


def write_env(master_key: str):
    """Create or update .env with the MASTER_KEY."""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        new_lines = []
        found = False
        for line in lines:
            if line.startswith("MASTER_KEY="):
                new_lines.append(f"MASTER_KEY={master_key}\n")
                found = True
            else:
                new_lines.append(line)
        if not found:
            new_lines.append(f"MASTER_KEY={master_key}\n")
    else:
        # Fresh install — create .env with all defaults
        new_lines = [DEFAULT_ENV, f"MASTER_KEY={master_key}\n"]

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def create_license(master_key: str) -> bool:
    """Generate a .license file for this machine using the provided key."""
    try:
        hardware_hash = get_hardware_fingerprint()
        signature = hmac_module.new(
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

        with open(LICENSE_FILE, "w", encoding="utf-8") as f:
            json.dump(license_data, f, indent=2)

        return True
    except Exception as e:
        print(f"License creation error: {e}")
        return False


def validate(master_key: str) -> bool:
    """Validate the key against the generated .license."""
    try:
        if not LICENSE_FILE.exists():
            return False
        with open(LICENSE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        current_hw = get_hardware_fingerprint()
        stored_hw = data.get("hardware_hash", "")
        if not hmac_module.compare_digest(current_hw, stored_hw):
            return False

        expected_sig = hmac_module.new(
            master_key.encode("utf-8"),
            stored_hw.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()
        stored_sig = data.get("signature", "")
        return hmac_module.compare_digest(expected_sig, stored_sig)
    except Exception:
        return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python setup_license.py <MASTER_KEY>")
        sys.exit(1)

    master_key = sys.argv[1].strip()

    if len(master_key) < 16:
        print("Key too short.")
        sys.exit(1)

    # Step 1: Create license for this machine
    if not create_license(master_key):
        sys.exit(1)

    # Step 2: Validate it
    if not validate(master_key):
        sys.exit(1)

    # Step 3: Write to .env
    write_env(master_key)

    print("OK")
    sys.exit(0)


if __name__ == "__main__":
    main()
