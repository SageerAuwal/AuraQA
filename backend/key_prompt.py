"""
AuraQA - Key Entry Popup
=========================
Shows a graphical popup window asking the user to enter the MASTER_KEY.
Validates the key (up to 3 attempts) using setup_license.py.

Exit codes:
  0 = key accepted, license created, .env updated
  1 = 3 failed attempts — access denied
  2 = user cancelled
"""

import sys
import subprocess
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable
MAX_ATTEMPTS = 3


def validate_key(key: str) -> bool:
    """Run setup_license.py with the provided key. Returns True if accepted."""
    result = subprocess.run(
        [PYTHON, str(BACKEND_DIR / "setup_license.py"), key],
        capture_output=True,
        text=True
    )
    return result.returncode == 0


def show_prompt():
    root = tk.Tk()
    root.withdraw()  # Hide the empty root window

    # ── Custom styled dialog ──────────────────────────────────────
    attempt = [0]
    result = [False]

    def try_key():
        attempt[0] += 1
        key = entry_var.get().strip()

        if not key:
            status_label.config(text="⚠ Please enter a key.", fg="#f59e0b")
            return

        status_label.config(text="⏳ Validating key...", fg="#94a3b8")
        dialog.update()

        if validate_key(key):
            result[0] = True
            dialog.destroy()
        else:
            remaining = MAX_ATTEMPTS - attempt[0]
            if remaining <= 0:
                status_label.config(text="🔒 Access denied. Too many attempts.", fg="#ef4444")
                dialog.update()
                dialog.after(2000, dialog.destroy)
            else:
                entry_var.set("")
                status_label.config(
                    text=f"❌ Invalid key. {remaining} attempt(s) remaining.",
                    fg="#ef4444"
                )

    def on_cancel():
        dialog.destroy()

    # ── Build the dialog window ───────────────────────────────────
    dialog = tk.Toplevel(root)
    dialog.title("AuraQA — License Required")
    dialog.resizable(False, False)
    dialog.configure(bg="#0f172a")
    dialog.geometry("480x280")

    # Center on screen
    dialog.update_idletasks()
    w = dialog.winfo_width()
    h = dialog.winfo_height()
    x = (dialog.winfo_screenwidth() // 2) - (w // 2)
    y = (dialog.winfo_screenheight() // 2) - (h // 2)
    dialog.geometry(f"+{x}+{y}")

    # Make dialog stay on top
    dialog.attributes("-topmost", True)
    dialog.focus_force()

    # Title
    tk.Label(
        dialog,
        text="🔐  AuraQA License Required",
        font=("Segoe UI", 14, "bold"),
        bg="#0f172a", fg="#10b981"
    ).pack(pady=(24, 4))

    # Subtitle
    tk.Label(
        dialog,
        text="This system is protected. Enter your MASTER_KEY to continue.",
        font=("Segoe UI", 9),
        bg="#0f172a", fg="#94a3b8",
        wraplength=420
    ).pack(pady=(0, 16))

    # Key entry field
    entry_var = tk.StringVar()
    entry = tk.Entry(
        dialog,
        textvariable=entry_var,
        font=("Consolas", 10),
        bg="#1e293b", fg="#f1f5f9",
        insertbackground="#10b981",
        relief="flat",
        width=48,
        show="•"
    )
    entry.pack(ipady=8, padx=30)
    entry.focus()

    # Status label
    status_label = tk.Label(
        dialog,
        text="",
        font=("Segoe UI", 9),
        bg="#0f172a", fg="#94a3b8"
    )
    status_label.pack(pady=(8, 0))

    # Buttons frame
    btn_frame = tk.Frame(dialog, bg="#0f172a")
    btn_frame.pack(pady=16)

    tk.Button(
        btn_frame,
        text="  Activate  ",
        command=try_key,
        font=("Segoe UI", 10, "bold"),
        bg="#10b981", fg="#ffffff",
        activebackground="#059669",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=12, pady=6
    ).pack(side="left", padx=8)

    tk.Button(
        btn_frame,
        text="  Cancel  ",
        command=on_cancel,
        font=("Segoe UI", 10),
        bg="#1e293b", fg="#94a3b8",
        activebackground="#334155",
        activeforeground="#ffffff",
        relief="flat",
        cursor="hand2",
        padx=12, pady=6
    ).pack(side="left", padx=8)

    # Allow Enter key to submit
    dialog.bind("<Return>", lambda e: try_key())
    dialog.protocol("WM_DELETE_WINDOW", on_cancel)

    root.wait_window(dialog)

    if result[0]:
        # Show success briefly
        root.deiconify()
        messagebox.showinfo(
            "AuraQA — Activated",
            "✅ License accepted!\n\nAuraQA will now start. Please wait..."
        )
        root.destroy()
        sys.exit(0)
    elif attempt[0] >= MAX_ATTEMPTS:
        root.deiconify()
        messagebox.showerror(
            "AuraQA — Access Denied",
            "🔒 Too many failed attempts.\nStartup has been cancelled."
        )
        root.destroy()
        sys.exit(1)
    else:
        # User clicked Cancel
        root.destroy()
        sys.exit(2)


if __name__ == "__main__":
    show_prompt()
