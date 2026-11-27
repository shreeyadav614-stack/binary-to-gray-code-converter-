"""
gray_core.py - everything except the window.

* loads the C++ engine (graycode.cpp) with ctypes, builds it if needed,
  and falls back to identical pure-Python code if that is not possible
* truth tables, logic equations, gate counts (K-map / XOR comparison)
* glitch statistics, encoder misread analysis
* asynchronous FIFO model with Gray-coded pointers
* Verilog generator for an FPGA board
"""
import ctypes, os, platform, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))

# ───────────────────────── C++ engine loader ─────────────────────────
def _bind(lib):
    S = ctypes.c_char_p
    lib.binary_to_gray.argtypes = [S, S];            lib.binary_to_gray.restype = ctypes.c_int
    lib.gray_to_binary.argtypes = [S, S];            lib.gray_to_binary.restype = ctypes.c_int
    lib.hamming_distance.argtypes = [S, S];          lib.hamming_distance.restype = ctypes.c_int
    lib.total_flips.argtypes = [ctypes.c_int] * 2;   lib.total_flips.restype = ctypes.c_longlong
    lib.flips_sequence.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.POINTER(ctypes.c_int)]
    lib.flips_sequence.restype = ctypes.c_int
    lib.worst_case_error.argtypes = [ctypes.c_int] * 2;  lib.worst_case_error.restype = ctypes.c_int
    lib.simulate_glitches.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_uint32]
    lib.simulate_glitches.restype = ctypes.c_int
    return lib

def load_engine():
    system = platform.system()
    ext = {"Windows": ".dll", "Darwin": ".dylib"}.get(system, ".so")
    lib_path = os.path.join(HERE, "graycode" + ext)
    src = os.path.join(HERE, "graycode.cpp")

    def build():
        flags = ["-shared", "-O2"] + ([] if system == "Windows" else ["-fPIC"])
        try:
            subprocess.run(["g++", *flags, src, "-o", lib_path], check=True, capture_output=True)
            return True
        except Exception:
            return False

    stale = os.path.exists(lib_path) and os.path.exists(src) and \
        os.path.getmtime(src) > os.path.getmtime(lib_path)
    if (not os.path.exists(lib_path) or stale) and not build():
        if not os.path.exists(lib_path):
            return None
    for _ in range(2):                         # second pass = rebuild an outdated library once
        try:
            return _bind(ctypes.CDLL(lib_path))
        except (OSError, AttributeError):
            if not build():
                return None
    return None

LIB = load_engine()
ENGINE = "C++ engine active" if LIB else "Python fallback (C++ library not built)"

# ───────────────────────── pure-Python mirror ─────────────────────────
def _popc(x): return bin(x).count("1")
def to_gray(v): return v ^ (v >> 1)
def from_gray(g):
    b = 0
    while g:
        b ^= g; g >>= 1
    return b
def _enc(v, gray): return to_gray(v) if gray else v
def _dec(c, gray): return from_gray(c) if gray else c

def _py_b2g(s): return s[0] + "".join(str(int(s[i-1]) ^ int(s[i])) for i in range(1, len(s)))
def _py_g2b(s):
    out = [s[0]]
    for i in range(1, len(s)):
        out.append(str(int(out[-1]) ^ int(s[i])))
    return "".join(out)

# ───────────────────────── public API ─────────────────────────
def valid_bits(text):
    return bool(text) and all(c in "01" for c in text)

def convert(text, mode):
    """mode 'b2g' or 'g2b'. Any width. Returns a string, or None if invalid."""
    if not valid_bits(text):
        return None
    if LIB:
        buf = ctypes.create_string_buffer(len(text) + 1)
        fn = LIB.binary_to_gray if mode == "b2g" else LIB.gray_to_binary
        return buf.value.decode() if fn(text.encode(), buf) == 0 else None
    return _py_b2g(text) if mode == "b2g" else _py_g2b(text)

def hamming(a, b):
    if len(a) != len(b) or not valid_bits(a) or not valid_bits(b):
        return None
    if LIB:
        return LIB.hamming_distance(a.encode(), b.encode())
    return sum(x != y for x, y in zip(a, b))

def total_flips(n, gray):
    if LIB:
        return LIB.total_flips(n, int(gray))
    size = 1 << n
    return sum(_popc(_enc(v, gray) ^ _enc((v + 1) % size, gray)) for v in range(size))

def flips_sequence(n, gray):
    size = 1 << n
    if LIB:
        arr = (ctypes.c_int * size)()
        LIB.flips_sequence(n, int(gray), arr)
        return list(arr)
    return [_popc(_enc(v, gray) ^ _enc((v + 1) % size, gray)) for v in range(size)]

def worst_case_error(n, gray):
    if LIB:
        return LIB.worst_case_error(n, int(gray))
    size, worst = 1 << n, 0
    for v in range(size):
        nx = (v + 1) % size
        a, b = _enc(v, gray), _enc(nx, gray)
        d = a ^ b
        s = d
        while True:
            dec = _dec(a ^ s, gray)
            worst = max(worst, min(abs(dec - v), abs(dec - nx)))
            if s == 0:
                break
            s = (s - 1) & d
    return worst

def simulate_glitches(n, gray, trials, seed=12345):
    if LIB:
        return LIB.simulate_glitches(n, int(gray), trials, seed)
    M = 0xFFFFFFFF
    state = seed or 2463534242
    def xs():
        nonlocal state
        state ^= (state << 13) & M; state ^= state >> 17; state ^= (state << 5) & M
        return state
    size, errors = 1 << n, 0
    for _ in range(trials):
        v = xs() & (size - 1); nx = (v + 1) & (size - 1)
        a, b = _enc(v, gray), _enc(nx, gray)
        dec = _dec(a ^ (xs() & (a ^ b)), gray)
        if dec != v and dec != nx:
            errors += 1
    return errors

def glitch_report(n, trials, seed=12345):
    """Everything the Glitch Lab shows, for binary and Gray counters."""
    rep = {"n": n, "trials": trials}
    for key, g in (("bin", False), ("gray", True)):
        rep[key] = {
            "flips": total_flips(n, g),
            "worst": worst_case_error(n, g) if n <= 12 else None,
            "errors": simulate_glitches(n, g, trials, seed),
            "seq": flips_sequence(n, g) if n <= 12 else [],
        }
    return rep

# ───────────────────────── logic view ─────────────────────────
def truth_table(n):
    """[(decimal, binary, gray)] for every n-bit value."""
    rows = []
    for v in range(1 << n):
        b = format(v, "0%db" % n)
        rows.append((v, b, convert(b, "b2g")))
    return rows

def equations(n, mode="b2g"):
    if mode == "b2g":
        eq = ["G%d = B%d" % (n - 1, n - 1)]
        eq += ["G%d = B%d \u2295 B%d" % (i, i + 1, i) for i in range(n - 2, -1, -1)]
    else:
        eq = ["B%d = G%d" % (n - 1, n - 1)]
        eq += ["B%d = B%d \u2295 G%d" % (i, i + 1, i) for i in range(n - 2, -1, -1)]
    return eq

def gate_stats(n):
    """Gate counts for the XOR form and for a plain two-level AND/OR/NOT (K-map SOP) form."""
    return {
        "xor_gates": n - 1,
        "xor_delay": 1,
        "sop_gates": 4 * n - 3,        # (n-1) outputs x (2 AND + 1 OR) + n shared NOT gates
        "g2b_delay": n - 1,            # Gray -> binary as a serial XOR chain
    }

# ───────────────────────── encoder disc ─────────────────────────
def disc_code(n, sector, gray):
    v = _enc(sector % (1 << n), gray)
    return format(v, "0%db" % n)

def boundary_readings(n, sector, gray):
    """All values a reader might decode while the disc moves from `sector` to the next."""
    size = 1 << n
    a, b = _enc(sector, gray), _enc((sector + 1) % size, gray)
    d = a ^ b
    seen, s = set(), d
    while True:
        seen.add(_dec(a ^ s, gray))
        if s == 0:
            break
        s = (s - 1) & d
    return sorted(seen)

# ───────────────────────── async FIFO with Gray pointers ─────────────────────────
class GrayFifo:
    """
    Asynchronous-FIFO controller model (Cummings style). Pointers have addr_bits+1 bits.
    The write pointer and read pointer are stored in binary for addressing and
    converted to Gray code (with the C++ engine) for the full / empty flags.
    """
    def __init__(self, addr_bits=3):
        self.a = addr_bits
        self.depth = 1 << addr_bits
        self.reset()

    def reset(self):
        self.mem = [None] * self.depth
        self.wptr = 0
        self.rptr = 0

    def _gray(self, ptr):
        return int(convert(format(ptr, "0%db" % (self.a + 1)), "b2g"), 2)

    @property
    def wgray(self): return self._gray(self.wptr)
    @property
    def rgray(self): return self._gray(self.rptr)

    @property
    def empty(self):
        return self.wgray == self.rgray

    @property
    def full(self):
        # full: same as read pointer but the two top bits inverted
        return self.wgray == (self.rgray ^ (0b11 << (self.a - 1)))

    @property
    def count(self):
        return (self.wptr - self.rptr) % (2 * self.depth)

    def push(self, value):
        if self.full:
            return False
        self.mem[self.wptr % self.depth] = value
        self.wptr = (self.wptr + 1) % (2 * self.depth)
        return True

    def pop(self):
        if self.empty:
            return None
        value = self.mem[self.rptr % self.depth]
        self.mem[self.rptr % self.depth] = None
        self.rptr = (self.rptr + 1) % (2 * self.depth)
        return value

    def pointer_text(self, ptr):
        w = self.a + 1
        return format(ptr, "0%db" % w), format(self._gray(ptr), "0%db" % w)

# ───────────────────────── Verilog generator ─────────────────────────
def verilog(n):
    return f"""// Binary <-> Gray converter, {n} bits  (generated by gray_core.py)
// Combinational logic only: binary->gray needs {n-1} XOR gates and one gate delay.

module bin2gray #(parameter N = {n}) (
    input  wire [N-1:0] bin,
    output wire [N-1:0] gray
);
    assign gray = bin ^ (bin >> 1);      // G[N-1] = B[N-1]; G[i] = B[i+1] ^ B[i]
endmodule

module gray2bin #(parameter N = {n}) (
    input  wire [N-1:0] gray,
    output wire [N-1:0] bin
);
    assign bin[N-1] = gray[N-1];
    genvar i;
    generate
        for (i = N-2; i >= 0; i = i - 1) begin : chain
            assign bin[i] = bin[i+1] ^ gray[i];
        end
    endgenerate
endmodule

// Board demo: switches in, LEDs show the Gray code.
// Map sw / led to the pins of your board in the constraints file (.xdc / .qsf / .pcf).
module top_demo #(parameter N = {n}) (
    input  wire [N-1:0] sw,
    output wire [N-1:0] led
);
    bin2gray #(.N(N)) u_b2g (.bin(sw), .gray(led));
endmodule

// Self-checking testbench: round trip + exactly one bit changes per count.
module tb_gray;
    localparam N = {n};
    reg  [N-1:0] bin;
    wire [N-1:0] gray, back;
    reg  [N-1:0] prev_gray;
    integer k, errors;

    bin2gray #(.N(N)) dut_b2g (.bin(bin),   .gray(gray));
    gray2bin #(.N(N)) dut_g2b (.gray(gray), .bin(back));

    initial begin
        errors = 0;
        prev_gray = 0;
        for (k = 0; k < (1 << N); k = k + 1) begin
            bin = k;
            #1;
            if (back !== bin) begin
                errors = errors + 1;
                $display("ROUND TRIP FAIL: %0d", k);
            end
            if (k > 0 && ((gray ^ prev_gray) & ((gray ^ prev_gray) - 1)) != 0) begin
                errors = errors + 1;
                $display("MORE THAN ONE BIT CHANGED at %0d", k);
            end
            prev_gray = gray;
        end
        if (errors == 0) $display("PASS: all %0d values OK", 1 << N);
        else             $display("FAIL: %0d errors", errors);
        $finish;
    end
endmodule
"""
