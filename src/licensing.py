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

def verify_license():
    if not os.path.exists(LIC_FILE):
        return False
    try:
        with open(LIC_FILE, "r") as f:
            enc_data = f.read()
        dec_data = encrypt_decrypt(base64.b64decode(enc_data.encode()).decode())
        lic_data = json.loads(dec_data)
        if lic_data["hwid"] == get_hwid():
            return True
    except:
        pass
    return False

def show_activation_screen():
    root = tk.Tk()
    root.title("Abiz Global - Activation Required")
    root.geometry("450x300")
    root.configure(bg="#F1F5F9")

    hwid = get_hwid()

    tk.Label(root, text="Software Locked", font=("Segoe UI", 16, "bold"), fg="#DC2626", bg="#F1F5F9").pack(pady=20)
    tk.Label(root, text="Your UUID / Hardware ID:", font=("Segoe UI", 10), bg="#F1F5F9").pack()

    id_ent = tk.Entry(root, width=40, justify="center")
    id_ent.insert(0, hwid)
    id_ent.config(state="readonly")
    id_ent.pack(pady=5)

    def copy_id():
        root.clipboard_clear()
        root.clipboard_append(hwid)
        messagebox.showinfo("Copied", "UUID copied to clipboard.")

    tk.Button(root, text="Copy UUID", command=copy_id, bg="#CBD5E1", relief="flat").pack(pady=5)

    def buy_now():
        try:
            # In real scenario, fetch config to get dynamic number
            # config = requests.get(CONFIG_URL).json()
            # num = config["whatsapp"]
            num = "1234567890" # fallback
            webbrowser.open(f"https://wa.me/{num}?text=I want to buy a license for Abiz Global Enterprise. My UUID is {hwid}")
        except:
            pass

    tk.Button(root, text="BUY NOW VIA WHATSAPP", command=buy_now, bg="#10B981", fg="white", font=("Segoe UI", 12, "bold"), relief="flat", cursor="hand2").pack(pady=20)

    root.mainloop()

if __name__ == "__main__":
    if not verify_license():
        show_activation_screen()
        import sys
        sys.exit(0)
    print("License Valid. Loading software...")
