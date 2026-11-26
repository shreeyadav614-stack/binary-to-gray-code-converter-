"""
Binary <-> Gray Code Converter
GUI: Python (tkinter)   |   Engine: C++ (graycode.cpp, loaded with ctypes)

Run:  python gray_gui.py
(The C++ library is compiled automatically if g++ is installed;
 otherwise a pure-Python fallback is used.)
"""
import ctypes, os, sys, subprocess, platform
import tkinter as tk
from tkinter import font as tkfont

HERE = os.path.dirname(os.path.abspath(__file__))

# ───────────────────────── C++ engine loader ─────────────────────────
def load_engine():
    system = platform.system()
    ext = {"Windows": ".dll", "Darwin": ".dylib"}.get(system, ".so")
    lib_path = os.path.join(HERE, "graycode" + ext)
    src = os.path.join(HERE, "graycode.cpp")

    if not os.path.exists(lib_path):
        flags = ["-shared", "-O2"] + ([] if system == "Windows" else ["-fPIC"])
        try:
            subprocess.run(["g++", *flags, src, "-o", lib_path],
                           check=True, capture_output=True)
        except Exception:
            return None
    try:
        lib = ctypes.CDLL(lib_path)
        for fn in (lib.binary_to_gray, lib.gray_to_binary):
            fn.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
            fn.restype = ctypes.c_int
        return lib
    except OSError:
        return None

LIB = load_engine()

def _py_b2g(s): return s[0] + "".join(str(int(s[i-1]) ^ int(s[i])) for i in range(1, len(s)))
def _py_g2b(s):
    out = [s[0]]
    for i in range(1, len(s)):
        out.append(str(int(out[-1]) ^ int(s[i])))
    return "".join(out)

def convert(text, mode):
    """mode: 'b2g' or 'g2b'. Returns converted string or None if invalid."""
    if not text or any(c not in "01" for c in text):
        return None
    if LIB:
        buf = ctypes.create_string_buffer(len(text) + 1)
        fn = LIB.binary_to_gray if mode == "b2g" else LIB.gray_to_binary
        return buf.value.decode() if fn(text.encode(), buf) == 0 else None
    return _py_b2g(text) if mode == "b2g" else _py_g2b(text)

# ───────────────────────────── Theme ─────────────────────────────
BG, CARD, CARD2 = "#0f1220", "#181c30", "#20253d"
TEXT, MUTED = "#e8eaf6", "#8a90b4"
ACCENT, ACCENT2 = "#7c5cff", "#00d4ff"
GOOD, BAD, WARN = "#2ee6a6", "#ff5c7a", "#ffb84d"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Binary ⇄ Gray Code Converter")
        self.geometry("820x720")
        self.minsize(720, 640)
        self.configure(bg=BG)
        self.mode = "b2g"
        self.var = tk.StringVar()
        self.var.trace_add("write", lambda *_: self.update_result())

        self.f_title = tkfont.Font(family="Segoe UI", size=22, weight="bold")
        self.f_norm = tkfont.Font(family="Segoe UI", size=11)
        self.f_small = tkfont.Font(family="Segoe UI", size=9)
        self.f_mono = tkfont.Font(family="Consolas", size=16, weight="bold")
        self.f_bit = tkfont.Font(family="Consolas", size=13, weight="bold")

        self.build()
        self.update_result()

    # ── UI construction ──
    def build(self):
        head = tk.Frame(self, bg=BG); head.pack(fill="x", padx=28, pady=(24, 6))
        tk.Label(head, text="Gray Code Converter", font=self.f_title,
                 bg=BG, fg=TEXT).pack(anchor="w")
        engine = "C++ engine active" if LIB else "Python fallback (C++ lib not built)"
        tk.Label(head, text="●  " + engine, font=self.f_small, bg=BG,
                 fg=GOOD if LIB else WARN).pack(anchor="w", pady=(2, 0))

        # mode toggle
        tog = tk.Frame(self, bg=CARD); tog.pack(fill="x", padx=28, pady=(14, 0))
        self.btn_b2g = self.make_tab(tog, "Binary  →  Gray", "b2g")
        self.btn_g2b = self.make_tab(tog, "Gray  →  Binary", "g2b")
        self.btn_b2g.pack(side="left", expand=True, fill="x", padx=4, pady=4)
        self.btn_g2b.pack(side="left", expand=True, fill="x", padx=4, pady=4)

        # input card
        card = tk.Frame(self, bg=CARD); card.pack(fill="x", padx=28, pady=14)
        self.lbl_in = tk.Label(card, text="", font=self.f_small, bg=CARD, fg=MUTED)
        self.lbl_in.pack(anchor="w", padx=18, pady=(14, 4))
        row = tk.Frame(card, bg=CARD2, highlightthickness=2,
                       highlightbackground=CARD2, highlightcolor=ACCENT)
        row.pack(fill="x", padx=18)
        self.entry = tk.Entry(row, textvariable=self.var, font=self.f_mono,
                              bg=CARD2, fg=TEXT, insertbackground=ACCENT2,
                              relief="flat", bd=0)
        self.entry.pack(side="left", fill="x", expand=True, padx=12, pady=10)
        self.entry.focus()
        tk.Button(row, text="✕", command=lambda: self.var.set(""), font=self.f_norm,
                  bg=CARD2, fg=MUTED, activebackground=CARD2, activeforeground=BAD,
                  relief="flat", bd=0, cursor="hand2").pack(side="right", padx=10)
        self.err = tk.Label(card, text="", font=self.f_small, bg=CARD, fg=BAD)
        self.err.pack(anchor="w", padx=18, pady=(4, 0))

        tk.Label(card, text="RESULT", font=self.f_small, bg=CARD, fg=MUTED
                 ).pack(anchor="w", padx=18, pady=(8, 4))
        rrow = tk.Frame(card, bg=CARD); rrow.pack(fill="x", padx=18, pady=(0, 16))
        self.result = tk.Label(rrow, text="—", font=self.f_mono, bg=CARD,
                               fg=ACCENT2, anchor="w", wraplength=520, justify="left")
        self.result.pack(side="left", fill="x", expand=True)
        self.copy_btn = tk.Button(rrow, text="Copy", command=self.copy, font=self.f_norm,
                                  bg=ACCENT, fg="white", activebackground="#947bff",
                                  activeforeground="white", relief="flat", bd=0,
                                  padx=18, pady=6, cursor="hand2")
        self.copy_btn.pack(side="right")

        # visualization
        vis = tk.Frame(self, bg=CARD); vis.pack(fill="both", expand=True, padx=28, pady=(0, 14))
        tk.Label(vis, text="STEP-BY-STEP VISUALIZATION", font=self.f_small,
                 bg=CARD, fg=MUTED).pack(anchor="w", padx=18, pady=(14, 4))
        self.canvas = tk.Canvas(vis, bg=CARD, height=210, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=18)
        self.canvas.bind("<Configure>", lambda e: self.draw())
        self.info = tk.Label(vis, text="", font=self.f_small, bg=CARD, fg=MUTED,
                             justify="left", anchor="w")
        self.info.pack(fill="x", padx=18, pady=(0, 14))

        tk.Label(self, text="Rule: G[0] = B[0]   |   G[i] = B[i-1] XOR B[i]",
                 font=self.f_small, bg=BG, fg=MUTED).pack(pady=(0, 12))

    def make_tab(self, parent, text, mode):
        b = tk.Button(parent, text=text, font=self.f_norm, relief="flat", bd=0,
                      cursor="hand2", pady=9, command=lambda: self.set_mode(mode))
        return b

    def set_mode(self, mode):
        self.mode = mode
        self.update_result()

    # ── logic ──
    def update_result(self):
        on, off = (self.btn_b2g, self.btn_g2b) if self.mode == "b2g" else (self.btn_g2b, self.btn_b2g)
        on.configure(bg=ACCENT, fg="white", activebackground=ACCENT)
        off.configure(bg=CARD, fg=MUTED, activebackground=CARD)
        self.lbl_in.configure(text="BINARY INPUT" if self.mode == "b2g" else "GRAY CODE INPUT")

        text = self.var.get().strip()
        self.data_in, self.data_out = text, None
        if not text:
            self.err.configure(text="")
            self.result.configure(text="—")
        else:
            out = convert(text, self.mode)
            if out is None:
                self.err.configure(text="⚠  Only 0 and 1 are allowed")
                self.result.configure(text="—")
            else:
                self.err.configure(text="")
                self.data_out = out
                self.result.configure(text=out)
        self.draw()

    def copy(self):
        if self.data_out:
            self.clipboard_clear(); self.clipboard_append(self.data_out)
            self.copy_btn.configure(text="Copied ✓", bg=GOOD, fg="#0f1220")
            self.after(1200, lambda: self.copy_btn.configure(text="Copy", bg=ACCENT, fg="white"))

    # ── drawing ──
    def draw(self):
        c = self.canvas; c.delete("all")
        a, b = self.data_in, self.data_out
        if not b:
            c.create_text(c.winfo_width() / 2, 100, fill=MUTED, font=self.f_norm,
                          text="Type a binary string to see the conversion")
            self.info.configure(text="")
            return
        n = len(a)
        W = max(c.winfo_width(), 300)
        size = max(18, min(46, (W - 20) // n - 6))
        gap = 6
        total = n * (size + gap) - gap
        x0 = max(10, (W - total) / 2)
        y_in, y_out = 40, 150
        src_lbl = "Binary" if self.mode == "b2g" else "Gray"
        dst_lbl = "Gray" if self.mode == "b2g" else "Binary"
        c.create_text(x0, 14, anchor="w", fill=MUTED, font=self.f_small, text=src_lbl)
        c.create_text(x0, 196, anchor="w", fill=MUTED, font=self.f_small, text=dst_lbl)

        for i in range(n):
            x = x0 + i * (size + gap)
            self.box(c, x, y_in, size, a[i], ACCENT if i == 0 else CARD2)
            self.box(c, x, y_out, size, b[i], GOOD if i == 0 else CARD2,
                     txt=BG if i == 0 else ACCENT2)
            cx = x + size / 2
            c.create_line(cx, y_in + size, cx, y_out, fill=ACCENT, width=1, dash=(3, 3))
            if i > 0:
                # XOR link from the previous bit
                src_prev = (x - gap - size / 2) if self.mode == "b2g" else None
                if self.mode == "b2g":
                    c.create_line(src_prev, y_in + size, cx, y_out, fill=ACCENT2, width=1)
                else:
                    px = x - gap - size / 2
                    c.create_line(px, y_out, cx, y_in + size, fill=ACCENT2, width=1)
            c.create_text(cx, (y_in + size + y_out) / 2, text="⊕" if i else "=",
                          fill=WARN, font=self.f_small)

        dec_a, dec_b = int(a, 2), int(b, 2)
        if self.mode == "b2g":
            self.info.configure(text=f"Decimal of binary input: {dec_a}      Decimal of Gray output: {dec_b}      Bits: {n}")
        else:
            self.info.configure(text=f"Decimal of Gray input: {dec_a}      Decimal of binary output: {dec_b}      Bits: {n}")

    def box(self, c, x, y, s, ch, fill, txt=TEXT):
        c.create_rectangle(x, y, x + s, y + s, fill=fill, outline="")
        c.create_text(x + s / 2, y + s / 2, text=ch, fill=txt,
                      font=("Consolas", max(9, int(s * 0.42)), "bold"))

if __name__ == "__main__":
    App().mainloop()
