import os
import uuid
import json
import base64
import tkinter as tk
from tkinter import simpledialog, messagebox
import webbrowser
import requests

LIC_FILE = "license.dat"
CONFIG_URL = "https://pastebin.com/raw/dummy_link" # Replace with actual config file (e.g., GDrive/Pastebin)

def get_hwid():
    return str(uuid.getnode())

def encrypt_decrypt(data, key="ABIZ_SECRET_KEY"):
    return "".join(chr(ord(c) ^ ord(k)) for c, k in zip(data, key * (len(data) // len(key) + 1)))

import datetime

def verify_license():
    if not os.path.exists(LIC_FILE):
        return False, "License file not found. Please place 'license.dat' in the directory."
    try:
        with open(LIC_FILE, "r") as f:
            enc_data = f.read()
        dec_data = encrypt_decrypt(base64.b64decode(enc_data.encode()).decode())
        lic_data = json.loads(dec_data)

        # Verify Expiry Date
        expiry_date = lic_data.get("expiry_date", "")
        if expiry_date:
            try:
                exp_date = datetime.datetime.strptime(expiry_date, "%Y-%m-%d")
                if datetime.datetime.now() > exp_date:
                    return False, f"License expired on {expiry_date}."
            except Exception as e:
                return False, "Invalid expiry date format."

        # Verify Device
        allowed_devices = lic_data.get("allowed_devices", [])
        if get_hwid() not in allowed_devices:
            return False, "This device is not authorized."

        return True, "License valid."
    except Exception as e:
        return False, f"Invalid or corrupted license file. {e}"

class HoverButton(tk.Button):
    def __init__(self, master, hover_color=None, **kw):
        tk.Button.__init__(self, master=master, **kw)
        self.defaultBackground = self["bg"]
        self.hoverBackground = hover_color if hover_color else self.defaultBackground
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)

    def on_enter(self, e):
        if self['state'] != 'disabled':
            self['bg'] = self.hoverBackground

    def on_leave(self, e):
        self['bg'] = self.defaultBackground

def show_activation_screen(error_msg="Software Locked"):
    root = tk.Tk()
    root.title("Abiz Global - Activation Required")
    root.geometry("550x450")
    root.configure(bg="#F8FAFC")
    root.resizable(False, False)

    hwid = get_hwid()

    # Top Header
    header = tk.Frame(root, bg="#1E293B", height=80)
    header.pack(fill=tk.X, side=tk.TOP)
    tk.Label(header, text="ABIZ GLOBAL ENTERPRISE", font=("Segoe UI", 18, "bold"), fg="white", bg="#1E293B").pack(pady=15)
    tk.Label(header, text="LICENSE ACTIVATION", font=("Segoe UI", 10), fg="#94A3B8", bg="#1E293B").pack(pady=(0, 10))

    # Main Content Area
    content = tk.Frame(root, bg="#FFFFFF", bd=1, relief="solid", highlightbackground="#E2E8F0", highlightthickness=1)
    content.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

    tk.Label(content, text="🔒 Software Locked", font=("Segoe UI", 14, "bold"), fg="#DC2626", bg="#FFFFFF").pack(pady=(10, 5))
    tk.Label(content, text="To use this software, you need a valid license file.\nPlease provide your Hardware ID to the administrator.", font=("Segoe UI", 10), fg="#475569", bg="#FFFFFF", justify="center").pack(pady=(0, 10))

    # UUID Area
    uuid_frame = tk.Frame(content, bg="#F1F5F9", bd=1, relief="solid", highlightbackground="#CBD5E1", highlightthickness=1)
    uuid_frame.pack(fill=tk.X, padx=10, pady=5)

    tk.Label(uuid_frame, text="Your Hardware ID:", font=("Segoe UI", 9, "bold"), fg="#1E293B", bg="#F1F5F9").pack(anchor="w", padx=10, pady=(10, 0))

    id_ent = tk.Entry(uuid_frame, font=("Courier", 11), fg="#334155", bg="#FFFFFF", relief="flat")
    id_ent.insert(0, hwid)
    id_ent.config(state="readonly")
    id_ent.pack(fill=tk.X, padx=10, pady=(5, 10))

    def copy_id():
        root.clipboard_clear()
        root.clipboard_append(hwid)
        messagebox.showinfo("Copied", "Hardware ID copied to clipboard.\nSend this ID to purchase your license.")

    HoverButton(uuid_frame, text="📋 Copy Hardware ID", command=copy_id, bg="#E2E8F0", hover_color="#CBD5E1", fg="#1E293B", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(pady=(0, 10))

    # Action Area
    def buy_now():
        try:
            num = "923490098654"
            webbrowser.open(f"https://wa.me/{num}?text=I want to buy a license for Abiz Global Enterprise. My Hardware ID is {hwid}")
        except:
            pass

    HoverButton(content, text="💬 PURCHASE LICENSE VIA WHATSAPP", command=buy_now, bg="#10B981", hover_color="#059669", fg="white", font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2", height=2).pack(fill=tk.X, padx=20, pady=(20, 10))

    def verify_again():
        is_valid, msg = verify_license()
        if is_valid:
            messagebox.showinfo("Success", "License validated successfully! Starting application...")
            root.destroy()
        else:
            messagebox.showerror("Validation Failed", msg)

    HoverButton(content, text="🔄 Verify Existing License", command=verify_again, bg="#3B82F6", hover_color="#2563EB", fg="white", font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2").pack(pady=5)

    root.mainloop()

if __name__ == "__main__":
    if not verify_license():
        show_activation_screen()
        import sys
        sys.exit(0)
    print("License Valid. Loading software...")
