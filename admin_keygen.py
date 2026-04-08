import tkinter as tk
from tkinter import messagebox
import json
import base64
from src.licensing import encrypt_decrypt

def generate_key():
    hwid = hwid_ent.get().strip()
    if not hwid:
        messagebox.showerror("Error", "Please enter UUID")
        return

    data = {
        "hwid": hwid,
        "type": "premium"
    }

    raw = json.dumps(data)
    enc = base64.b64encode(encrypt_decrypt(raw).encode()).decode()

    with open("generated_license.dat", "w") as f:
        f.write(enc)

    messagebox.showinfo("Success", "License file generated successfully!")

root = tk.Tk()
root.title("Admin Key Generator")
root.geometry("300x200")
root.configure(bg="#1E293B")

tk.Label(root, text="Admin Key Generator", font=("Segoe UI", 14, "bold"), bg="#1E293B", fg="white").pack(pady=10)

tk.Label(root, text="Client UUID:", bg="#1E293B", fg="white").pack()
hwid_ent = tk.Entry(root, width=30)
hwid_ent.pack(pady=5)

tk.Button(root, text="Generate License File", command=generate_key, bg="#10B981", fg="white", relief="flat").pack(pady=20)

root.mainloop()
