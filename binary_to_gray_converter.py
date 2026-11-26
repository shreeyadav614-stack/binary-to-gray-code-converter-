import tkinter as tk
from tkinter import messagebox
import subprocess
import os

def convert():
    binary = entry.get().strip()

    if len(binary) != 4 or any(
        bit not in "01" for bit in binary
    ):
        messagebox.showerror(
            "Error", "Enter a valid 4-bit binary number"
        )
        return

    try:
        exe = "converter.exe" if os.name == "nt" else "./converter"

        result = subprocess.run(
            [exe, binary],
            capture_output=True,
            text=True,
            check=True
        )

        output.config(text=result.stdout.strip())

    except Exception:
        messagebox.showerror(
            "Error", "Unable to run C program"
        )

def clear():
    entry.delete(0, tk.END)
    output.config(text="")

root = tk.Tk()
root.title("Binary to Gray Converter")
root.geometry("400x300")

tk.Label(
    root, text="Binary to Gray Code Converter",
    font=("Arial", 16, "bold")
).pack(pady=20)

entry = tk.Entry(root, font=("Arial", 16))
entry.pack(pady=10)

tk.Button(
    root, text="Convert", command=convert
).pack(pady=8)

tk.Button(
    root, text="Clear", command=clear
).pack(pady=5)

tk.Label(root, text="Gray Code:").pack(pady=10)

output = tk.Label(
    root, text="", font=("Arial", 18, "bold")
)
output.pack()

root.mainloop()
