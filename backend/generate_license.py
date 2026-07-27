"""
AuraQA License Generator
=========================
Run this script ONCE on your machine to generate:
  1. A strong MASTER_KEY (your secret passphrase)
  2. A hardware-bound .license file for this machine

Usage:
    python generate_license.py

After running:
  - Your .env file will be updated with the new MASTER_KEY
  - A .license file will be created in the backend/ folder
  - Back up BOTH files privately (USB drive, personal cloud)

WARNING: If you lose these files, you cannot run AuraQA again
         without regenerating them on the same machine.
"""

import os
import sys
import secrets
import json
from pathlib import Path

# Ensure we can import from backend/app/
BACKEND_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BACKEND_DIR))

from app.security.license_check import (
    get_hardware_fingerprint,
    generate_license_file,
    _LICENSE_FILE,
    _PROJECT_ROOT,
)

ENV_FILE = BACKEND_DIR / ".env"


def generate_master_key(length: int = 48) -> str:
    """Generate a cryptographically secure random master key."""
    return secrets.token_hex(length)


def update_env_file(master_key: str):
    """Add or update MASTER_KEY in the .env file."""
    lines = []
    found = False

    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()

    new_lines = []
    for line in lines:
        if line.startswith("MASTER_KEY="):
            new_lines.append(f"MASTER_KEY={master_key}\n")
            found = True
        else:
            new_lines.append(line)

    if not found:
        new_lines.append(f"\n# AuraQA License Passkey (auto-generated — keep private!)\n")
        new_lines.append(f"MASTER_KEY={master_key}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)


def main():
    print()
    print("=" * 60)
    print("  AuraQA License Generator")
    print("=" * 60)

    # ── Check if license already exists ──────────────────────────
    if _LICENSE_FILE.exists():
        print()
        print("  WARNING: A .license file already exists.")
        answer = input("  Regenerate it? This will invalidate the old license. (yes/no): ").strip().lower()
        if answer != "yes":
            print("  Cancelled. Existing license kept.")
            print()
            return

    # ── Generate master key ───────────────────────────────────────
    print()
    print("  [1/3] Generating secure MASTER_KEY...")
    master_key = generate_master_key()
    print(f"  MASTER_KEY = {master_key[:12]}...{master_key[-8:]} (hidden for security)")

    # ── Generate hardware fingerprint ─────────────────────────────
    print()
    print("  [2/3] Reading hardware fingerprint of this machine...")
    fingerprint = get_hardware_fingerprint()
    print(f"  Hardware ID = {fingerprint[:16]}...{fingerprint[-8:]} (partial, for security)")

    # ── Write .license file ───────────────────────────────────────
    print()
    print("  [3/3] Writing .license file and updating .env...")
    license_data = generate_license_file(master_key)
    update_env_file(master_key)

    # ── Done ──────────────────────────────────────────────────────
    print()
    print("=" * 60)
    print("  License Generated Successfully!")
    print("=" * 60)
    print()
    print(f"  .license file : {_LICENSE_FILE}")
    print(f"  .env file     : {ENV_FILE}")
    print()
    print("  IMPORTANT — Back these up privately right now:")
    print("    1. backend/.license")
    print("    2. backend/.env  (contains your MASTER_KEY)")
    print()
    print("  Without these TWO files, AuraQA cannot run.")
    print("  They are NOT pushed to GitHub — keep them safe!")
    print()
    print("=" * 60)
    print()

    # Show the full key once — user should write it down
    print("  YOUR MASTER_KEY (write this down safely):")
    print(f"  {master_key}")
    print()
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
