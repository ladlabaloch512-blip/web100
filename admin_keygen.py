import tkinter as tk
from tkinter import messagebox
import json
import base64
from src.licensing import encrypt_decrypt
import datetime

def generate_key():
    hwids = hwid_ent.get().strip()
    expiry = expiry_ent.get().strip()

    if not hwids:
        messagebox.showerror("Error", "Please enter at least one UUID.")
        return

    if expiry:
        try:
            datetime.datetime.strptime(expiry, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Error", "Invalid expiry date format. Use YYYY-MM-DD.")
            return

    # Parse multiple UUIDs separated by comma
    allowed_devices = [h.strip() for h in hwids.split(",") if h.strip()]

    data = {
        "allowed_devices": allowed_devices,
        "expiry_date": expiry,
        "type": "premium"
    }

    raw = json.dumps(data)
    enc = base64.b64encode(encrypt_decrypt(raw).encode()).decode()

    with open("license.dat", "w") as f:
        f.write(enc)

    messagebox.showinfo("Success", "license.dat file generated successfully in the current directory!")

root = tk.Tk()
root.title("Admin Key Generator")
root.geometry("400x350")
root.configure(bg="#1E293B")

tk.Label(root, text="Admin Key Generator", font=("Segoe UI", 16, "bold"), bg="#1E293B", fg="white").pack(pady=15)

# Hardware IDs
frame1 = tk.Frame(root, bg="#1E293B")
frame1.pack(fill=tk.X, padx=20, pady=5)
tk.Label(frame1, text="Allowed UUIDs (Comma separated):", font=("Segoe UI", 10), bg="#1E293B", fg="white").pack(anchor="w")
hwid_ent = tk.Entry(frame1, width=50, font=("Segoe UI", 10))
hwid_ent.pack(pady=5)

# Expiry Date
frame2 = tk.Frame(root, bg="#1E293B")
frame2.pack(fill=tk.X, padx=20, pady=15)
tk.Label(frame2, text="Expiry Date (YYYY-MM-DD) [Optional]:", font=("Segoe UI", 10), bg="#1E293B", fg="white").pack(anchor="w")
expiry_ent = tk.Entry(frame2, width=50, font=("Segoe UI", 10))
expiry_ent.pack(pady=5)
tk.Label(frame2, text="Leave blank for lifetime access.", font=("Segoe UI", 8, "italic"), bg="#1E293B", fg="#94A3B8").pack(anchor="w")

tk.Button(root, text="Generate License File (license.dat)", command=generate_key, bg="#10B981", fg="white", font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2").pack(pady=25)

root.mainloop()
