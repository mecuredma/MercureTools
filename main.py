"""
MercureTools v1.0.0 - AIO management tool for PCIe FPGA boards (Artix-7 35T / 75T / 100T).

Single-file CustomTkinter application, ready for PyInstaller.
External helpers (OpenOCD, installers, benchmark tools) are looked up in a "tools"
folder placed next to main.py / the built executable. Anything missing is reported
in the console instead of crashing the app.

    tools/openocd/bin/openocd.exe          (or openocd on PATH)
    tools/cfg/flash_35T.cfg, flash_75T.cfg, flash_100T.cfg   (your flashing scripts)
    tools/drivers/FTD3XX_Driver.exe, CH341SER.EXE, CH343SER.EXE
    tools/speedtest/SpeedTest.exe, tools/dmatest/DMATestTool.exe
    tools/makcu/MakcuAIO.exe
"""

import ctypes
import os
import queue
import random
import re
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import Canvas, filedialog

import customtkinter as ctk
from PIL import Image, ImageDraw

APP_NAME = "MercureTools"
APP_VERSION = "1.0.0"
DISCORD_URL = "https://discord.gg/UpywRnsTAA"

# ----------------------------------------------------------------------------- theme
BG = "#0b0c10"
BG_DEEP = "#07080b"
SIDEBAR = "#0d0e13"
CARD = "#11131a"
CARD_HI = "#161924"
BORDER = "#1f2433"
SILVER = "#d5dbe8"
MUTED = "#7b8499"
ACCENT = "#8fb4ff"
ACCENT_DIM = "#3a4a73"
ACCENT_BG = "#151a2b"
DANGER = "#ff6b7d"
DANGER_BG = "#1e1015"
OK = "#6fe3b0"
WARN = "#e8c27a"

FONT = "Segoe UI"
MONO = "Consolas"

LEVEL_COLORS = {"INFO": "#9fb4d8", "OK": OK, "WARN": WARN, "ERR": DANGER}

BOARDS = ["35T", "75T", "100T"]
BOARD_LABELS = {
    "35T": "35T (Squirrel / Screamer)",
    "75T": "75T (Enigma X1 / Raptor)",
    "100T": "100T (ZDMA / Gbox)",
}

# Artix-7 JTAG IDCODEs (version nibble masked out)
XILINX_IDS = {
    0x0362D093: ("XC7A35T", "35T"),
    0x03631093: ("XC7A75T", "75T"),
    0x03632093: ("XC7A100T", "100T"),
}

# OpenOCD interface scripts - edit to match the OpenOCD build you ship.
INTERFACES = {
    "CH347": "interface/ch347.cfg",
    "FTDI": "interface/ftdi/um232h.cfg",
}

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


# ----------------------------------------------------------------------------- helpers
def tools_dir() -> Path:
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    return base / "tools"


TOOLS = tools_dir()


def find_openocd():
    for candidate in (TOOLS / "openocd" / "bin" / "openocd.exe", TOOLS / "openocd.exe"):
        if candidate.exists():
            return str(candidate)
    return shutil.which("openocd")


def blend(c1: str, c2: str, t: float) -> str:
    a = [int(c1[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(c2[i:i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{int(a[i] + (b[i] - a[i]) * t):02x}" for i in range(3))


def enable_dark_titlebar(win):
    if sys.platform != "win32":
        return
    try:
        win.update()
        hwnd = ctypes.windll.user32.GetParent(win.winfo_id())
        for attr in (20, 19):  # DWMWA_USE_IMMERSIVE_DARK_MODE (new / old build)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, attr, ctypes.byref(ctypes.c_int(1)), 4)
    except Exception:
        pass


def make_planet_icon(size: int) -> ctk.CTkImage:
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    c, r = s / 2, s * 0.26
    for i in range(10, 0, -1):  # corona
        rr = r + i * s * 0.012
        col = (143, 180, 255, int(10 + (10 - i) * 4))
        d.ellipse((c - rr, c - rr, c + rr, c + rr), fill=col)
    d.arc((s * 0.04, c - s * 0.12, s * 0.96, c + s * 0.12), 180, 360, fill=(213, 219, 232, 200), width=int(s * 0.025))
    d.ellipse((c - r, c - r, c + r, c + r), fill=(4, 5, 8, 255), outline=(170, 182, 208, 255), width=int(s * 0.02))
    d.arc((c - r, c - r, c + r, c + r), -55, 40, fill=(235, 242, 255, 255), width=int(s * 0.045))
    d.arc((s * 0.04, c - s * 0.12, s * 0.96, c + s * 0.12), 0, 180, fill=(213, 219, 232, 255), width=int(s * 0.025))
    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def make_discord_icon(size: int) -> ctk.CTkImage:
    s = size * 4
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, s * 0.12, s, s * 0.88), radius=s * 0.3, fill=(88, 101, 242, 255))
    for x in (0.32, 0.68):
        d.ellipse((s * (x - 0.1), s * 0.38, s * (x + 0.1), s * 0.62), fill=(255, 255, 255, 255))
    img = img.resize((size, size), Image.LANCZOS)
    return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))


def launch_file(app, path: Path, label: str):
    if not path.exists():
        app.log(f"{label} not found: {path}", "WARN")
        return
    try:
        if sys.platform == "win32":
            os.startfile(str(path))  # noqa: S606
        else:
            subprocess.Popen([str(path)])
        app.log(f"{label} launched.", "OK")
    except Exception as exc:
        app.log(f"Could not launch {label}: {exc}", "ERR")


# ----------------------------------------------------------------------------- backend
class ToolMissing(Exception):
    pass


def run_openocd(args, timeout=25) -> str:
    exe = find_openocd()
    if not exe:
        raise ToolMissing("OpenOCD not found. Put it in tools/openocd/bin or add it to PATH.")
    proc = subprocess.run(
        [exe, *args], capture_output=True, text=True, timeout=timeout, creationflags=NO_WINDOW
    )
    return (proc.stdout or "") + (proc.stderr or "")


def interface_candidates(choice: str):
    return list(INTERFACES.items()) if choice == "Auto" else [(choice, INTERFACES[choice])]


def detect_chip(iface_choice: str, log):
    """Return dict(chip, idcode, interface, board) or None."""
    for name, cfg in interface_candidates(iface_choice):
        log(f"Probing JTAG chain via {name} ...", "INFO")
        out = run_openocd([
            "-f", cfg,
            "-c", "transport select jtag",
            "-c", "adapter speed 10000",
            "-c", "jtag newtap chip tap -irlen 6 -ignore-version",
            "-c", "init", "-c", "scan_chain", "-c", "exit",
        ])
        for m in re.finditer(r"0x([0-9a-fA-F]{8})", out):
            code = int(m.group(1), 16) & 0x0FFFFFFF
            if code in XILINX_IDS:
                chip, board = XILINX_IDS[code]
                return {"chip": chip, "idcode": f"0x{code:08X}", "interface": name, "board": board}
        log(f"No Artix-7 found on {name}.", "WARN")
    return None


def read_device_dna(iface_choice: str, log):
    """Read the 57-bit Device DNA via the FUSE_DNA instruction (0x32)."""
    for name, cfg in interface_candidates(iface_choice):
        log(f"Reading Device DNA via {name} ...", "INFO")
        out = run_openocd([
            "-f", cfg,
            "-c", "transport select jtag",
            "-c", "adapter speed 10000",
            "-c", "jtag newtap xc7 tap -irlen 6 -ignore-version",
            "-c", "init",
            "-c", "irscan xc7.tap 0x32",
            "-c", "drscan xc7.tap 64 0x0",
            "-c", "exit",
        ])
        hits = re.findall(r"^\s*([0-9a-fA-F]{8,16})\s*$", out, re.MULTILINE)
        if hits:
            value = int(hits[-1], 16) & ((1 << 57) - 1)
            return f"0x{value:015X}"
    return None


class ProcessRunner:
    """Runs one external process, streams its output line by line."""

    def __init__(self, app):
        self.app, self.proc = app, None

    @property
    def running(self):
        return self.proc is not None and self.proc.poll() is None

    def start(self, cmd, on_line, on_done):
        if self.running:
            return

        def work():
            code = -1
            try:
                self.proc = subprocess.Popen(
                    cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    bufsize=1, creationflags=NO_WINDOW,
                )
                for line in self.proc.stdout:
                    self.app.post(on_line, line.rstrip())
                code = self.proc.wait()
            except Exception as exc:
                self.app.post(on_line, f"[error] {exc}")
            self.app.post(on_done, code)

        threading.Thread(target=work, daemon=True).start()

    def kill(self):
        if self.running:
            self.proc.kill()


# ----------------------------------------------------------------------------- widgets
def make_button(master, text, command, kind="normal", **kw):
    palette = {
        "normal": dict(fg_color=CARD_HI, border_color=BORDER, hover_color="#1c2132", text_color=SILVER),
        "glow": dict(fg_color=ACCENT_BG, border_color=ACCENT, hover_color="#1d2540", text_color="#eaf1ff"),
        "danger": dict(fg_color=DANGER_BG, border_color=DANGER, hover_color="#2a141b", text_color="#ffd9de"),
        "small": dict(fg_color=CARD_HI, border_color=BORDER, hover_color="#1c2132", text_color=MUTED),
    }[kind]
    size = 11 if kind == "small" else 13
    btn = ctk.CTkButton(
        master, text=text, command=command, border_width=1, corner_radius=10,
        font=ctk.CTkFont(FONT, size, "bold" if kind != "small" else "normal"),
        height=28 if kind == "small" else 40, **palette, **kw,
    )
    if kind == "glow":
        btn.bind("<Enter>", lambda e: btn.configure(border_color="#c4d7ff", border_width=2), add="+")
        btn.bind("<Leave>", lambda e: btn.configure(border_color=ACCENT, border_width=1), add="+")
    return btn


def make_card(master, **kw):
    return ctk.CTkFrame(master, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=14, **kw)


def card_title(master, text):
    return ctk.CTkLabel(master, text=text, font=ctk.CTkFont(FONT, 12, "bold"), text_color=ACCENT, anchor="w")


def make_log_box(master, **kw):
    box = ctk.CTkTextbox(
        master, fg_color=BG_DEEP, border_color=BORDER, border_width=1, corner_radius=10,
        text_color="#9fb4d8", font=(MONO, 11), wrap="word", **kw,
    )
    for lvl, col in LEVEL_COLORS.items():
        box.tag_config(lvl, foreground=col)
    box.configure(state="disabled")
    return box


def append_text(box, text, tag="INFO"):
    box.configure(state="normal")
    box.insert("end", text + "\n", tag)
    box.see("end")
    box.configure(state="disabled")


class BaseView(ctk.CTkFrame):
    def __init__(self, app, parent, title, subtitle):
        super().__init__(parent, fg_color="transparent")
        self.app = app
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(FONT, 24, "bold"), text_color=SILVER, anchor="w").pack(fill="x")
        ctk.CTkLabel(self, text=subtitle, font=ctk.CTkFont(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", pady=(2, 14))

    def on_show(self):
        pass


class EclipseArt(Canvas):
    """Eclipse with a thin corona and planetary rings, redrawn on resize."""

    def __init__(self, master):
        super().__init__(master, bg=BG, highlightthickness=0, bd=0)
        self.bind("<Configure>", lambda e: self.draw())

    def draw(self):
        self.delete("all")
        w, h = self.winfo_width(), self.winfo_height()
        if w < 80 or h < 80:
            return
        rnd = random.Random(7)
        for _ in range(70):
            x, y = rnd.randint(0, w), rnd.randint(0, h)
            self.create_oval(x, y, x + 1, y + 1, fill=blend(BG, SILVER, rnd.uniform(0.15, 0.55)), outline="")
        cx, cy = w / 2, h / 2
        r = min(w * 0.18, h * 0.34)
        steps = 26
        for i in range(steps, 0, -1):  # corona
            rr = r + i * r * 0.04
            t = ((steps - i) / steps) ** 2.4 * 0.42
            self.create_oval(cx - rr, cy - rr, cx + rr, cy + rr, fill=blend(BG, "#5b8def", t), outline="")
        rings = [(2.5, 0.55, 0.55), (2.0, 0.44, 0.35), (3.1, 0.68, 0.22)]
        for sx, sy, a in rings:  # back half
            self.create_arc(cx - r * sx, cy - r * sy, cx + r * sx, cy + r * sy, start=0, extent=180,
                            style="arc", outline=blend(BG, SILVER, a), width=1)
        self.create_oval(cx - r, cy - r, cx + r, cy + r, fill="#000000", outline=blend(BG, SILVER, 0.5))
        self.create_arc(cx - r, cy - r, cx + r, cy + r, start=-55, extent=100, style="arc",
                        outline="#e8efff", width=2)  # bright limb
        for sx, sy, a in rings:  # front half
            self.create_arc(cx - r * sx, cy - r * sy, cx + r * sx, cy + r * sy, start=180, extent=180,
                            style="arc", outline=blend(BG, SILVER, a + 0.15), width=1)


# ----------------------------------------------------------------------------- views
class AutoDetectView(BaseView):
    FIELDS = ["Chip", "IDCODE", "Interface", "Selected Board"]

    def __init__(self, app, parent):
        super().__init__(app, parent, "Hardware Auto-Detect", "Detect the Artix-7 chip via the IDCODE JTAG")
        card = make_card(self)
        card.pack(fill="x")
        card_title(card, "Detected hardware").pack(fill="x", padx=20, pady=(16, 6))
        self.values = {}
        for i, name in enumerate(self.FIELDS):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=20)
            ctk.CTkLabel(row, text=name, width=140, anchor="w", font=ctk.CTkFont(FONT, 13), text_color=MUTED).pack(side="left", pady=9)
            val = ctk.CTkLabel(row, text="-", anchor="w", font=ctk.CTkFont(MONO, 14), text_color=SILVER)
            val.pack(side="left", fill="x", expand=True)
            self.values[name] = val
            if i < len(self.FIELDS) - 1:
                ctk.CTkFrame(card, height=1, fg_color=BORDER).pack(fill="x", padx=20)
        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(14, 18))
        self.btn = make_button(bottom, "Start Detection", self.start, "glow", width=190)
        self.btn.pack(side="left")
        self.status = ctk.CTkLabel(bottom, text="Ready", font=ctk.CTkFont(FONT, 12), text_color=MUTED)
        self.status.pack(side="left", padx=14)
        EclipseArt(self).pack(fill="both", expand=True, pady=(12, 0))
        self.refresh_board()
        app.board_listeners.append(self.refresh_board)

    def refresh_board(self):
        self.values["Selected Board"].configure(text=self.app.board_var.get())

    def start(self):
        self.btn.configure(state="disabled")
        self.status.configure(text="Scanning JTAG chain ...", text_color=ACCENT)
        self.app.log("Auto-detect started.")

        def work():
            try:
                res = detect_chip(self.app.iface_var.get(), self.app.log_threadsafe)
                self.app.post(self.finish, res, None)
            except ToolMissing as exc:
                self.app.post(self.finish, None, str(exc))
            except Exception as exc:
                self.app.post(self.finish, None, f"Detection failed: {exc}")

        threading.Thread(target=work, daemon=True).start()

    def finish(self, res, error):
        self.btn.configure(state="normal")
        if res:
            self.values["Chip"].configure(text=res["chip"])
            self.values["IDCODE"].configure(text=res["idcode"])
            self.values["Interface"].configure(text=res["interface"])
            self.app.select_board(res["board"])
            self.status.configure(text="Device found", text_color=OK)
            self.app.set_hardware(f"{res['chip']} connected", True)
            self.app.log(f"Detected {res['chip']} ({res['idcode']}) via {res['interface']}.", "OK")
        else:
            self.status.configure(text=error or "No device found", text_color=DANGER)
            self.app.set_hardware("No hardware connected", False)
            self.app.log(error or "No Artix-7 device found on the JTAG chain.", "ERR")


class DNAView(BaseView):
    def __init__(self, app, parent):
        super().__init__(app, parent, "DNA Grabber", "Read the unique 57-bit Xilinx Device DNA of the connected chip via JTAG")
        card = make_card(self)
        card.pack(fill="x")
        card_title(card, "Device DNA").pack(fill="x", padx=20, pady=(16, 8))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20)
        self.field = ctk.CTkEntry(row, height=42, fg_color=BG_DEEP, border_color=BORDER, text_color=SILVER,
                                  font=ctk.CTkFont(MONO, 14), corner_radius=10)
        self.field.pack(side="left", fill="x", expand=True)
        self.set_value("0x000000000000000  (click 'Read Device DNA')")
        make_button(row, "Copy DNA", self.copy, "normal", width=120).pack(side="left", padx=(10, 0))
        bottom = ctk.CTkFrame(card, fg_color="transparent")
        bottom.pack(fill="x", padx=20, pady=(14, 18))
        self.btn = make_button(bottom, "Read Device DNA", self.read, "glow", width=190)
        self.btn.pack(side="left")
        self.status = ctk.CTkLabel(bottom, text="Ready", font=ctk.CTkFont(FONT, 12), text_color=MUTED)
        self.status.pack(side="left", padx=14)
        note = make_card(self)
        note.pack(fill="x", pady=(12, 0))
        ctk.CTkLabel(
            note, justify="left", anchor="w", font=ctk.CTkFont(FONT, 12), text_color=MUTED,
            text="DNA is read through OpenOCD over JTAG. Connect your JTAG cable first.\n"
                 "The value is burned into the silicon and unique to each chip.",
        ).pack(fill="x", padx=20, pady=12)
        EclipseArt(self).pack(fill="both", expand=True, pady=(12, 0))

    def set_value(self, text):
        self.field.configure(state="normal")
        self.field.delete(0, "end")
        self.field.insert(0, text)
        self.field.configure(state="readonly")

    def copy(self):
        text = self.field.get().split()[0]
        self.app.clipboard_clear()
        self.app.clipboard_append(text)
        self.app.log("DNA copied to clipboard.", "OK")

    def read(self):
        self.btn.configure(state="disabled")
        self.status.configure(text="Reading ...", text_color=ACCENT)

        def work():
            try:
                dna = read_device_dna(self.app.iface_var.get(), self.app.log_threadsafe)
                self.app.post(self.finish, dna, None if dna else "No DNA returned. Check the JTAG connection.")
            except ToolMissing as exc:
                self.app.post(self.finish, None, str(exc))
            except Exception as exc:
                self.app.post(self.finish, None, f"DNA read failed: {exc}")

        threading.Thread(target=work, daemon=True).start()

    def finish(self, dna, error):
        self.btn.configure(state="normal")
        if dna:
            self.set_value(dna)
            self.status.configure(text="DNA read", text_color=OK)
            self.app.log(f"Device DNA: {dna}", "OK")
        else:
            self.status.configure(text="Failed", text_color=DANGER)
            self.app.log(error, "ERR")


class SpeedTestView(BaseView):
    TOOL_PATHS = {
        "Lone's Speed Test": TOOLS / "speedtest" / "SpeedTest.exe",
        "Neko's DMATestTool": TOOLS / "dmatest" / "DMATestTool.exe",
    }

    def __init__(self, app, parent):
        super().__init__(app, parent, "Speed Test", "Benchmark raw PCIe physical memory read / write throughput")
        self.runner = ProcessRunner(app)
        self.grid_columnconfigure(0, weight=1, uniform="c")
        self.grid_columnconfigure(1, weight=1, uniform="c")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True)
        body.grid_columnconfigure((0, 1), weight=1, uniform="c")
        body.grid_rowconfigure(0, weight=1)
        left = make_card(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        card_title(left, "Benchmark tool").pack(fill="x", padx=18, pady=(16, 8))
        self.tool = ctk.CTkSegmentedButton(
            left, values=list(self.TOOL_PATHS), fg_color=BG_DEEP, selected_color=ACCENT_BG,
            selected_hover_color="#1d2540", unselected_color=BG_DEEP, unselected_hover_color=CARD_HI,
            text_color=SILVER, font=ctk.CTkFont(FONT, 12, "bold"), height=34,
        )
        self.tool.set("Lone's Speed Test")
        self.tool.pack(fill="x", padx=18)
        self.start_btn = make_button(left, "Start Speed Benchmark", self.start, "glow")
        self.start_btn.pack(fill="x", padx=18, pady=(14, 8))
        make_button(left, "Stop Test", self.runner.kill, "danger").pack(fill="x", padx=18)
        right = make_card(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        card_title(right, "Live benchmark stream").pack(fill="x", padx=18, pady=(16, 8))
        self.stream = make_log_box(right)
        self.stream.pack(fill="both", expand=True, padx=18, pady=(0, 18))
        append_text(self.stream, "=== Benchmark ready ===\nPick a tool and press Start Speed Benchmark.", "OK")

    def start(self):
        name = self.tool.get()
        exe = self.TOOL_PATHS[name]
        if not exe.exists():
            self.app.log(f"{name} not found: {exe}", "WARN")
            append_text(self.stream, f"{name} not found.\nExpected at: {exe}", "WARN")
            return
        self.start_btn.configure(state="disabled")
        append_text(self.stream, f"--- {name} ---", "OK")
        self.app.log(f"Running {name}.")
        self.runner.start(
            [str(exe)], lambda line: append_text(self.stream, line), self.done
        )

    def done(self, code):
        self.start_btn.configure(state="normal")
        append_text(self.stream, f"--- finished (exit code {code}) ---", "OK" if code == 0 else "WARN")
        self.app.log(f"Benchmark finished (exit code {code}).", "OK" if code == 0 else "WARN")


class DriversView(BaseView):
    def __init__(self, app, parent):
        super().__init__(app, parent, "Drivers", "Install the USB data and JTAG drivers required by your board")
        card = make_card(self)
        card.pack(fill="x")
        card_title(card, "Hardware drivers").pack(fill="x", padx=20, pady=(16, 4))
        ctk.CTkLabel(card, text="Launches the signed installers from the tools/drivers folder.",
                     font=ctk.CTkFont(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", padx=20, pady=(0, 10))
        d = TOOLS / "drivers"
        make_button(card, "Install Data Driver  (FTDI FTD3XX)",
                    lambda: launch_file(app, d / "FTD3XX_Driver.exe", "FTD3XX driver installer")).pack(fill="x", padx=20, pady=(0, 8))
        make_button(card, "Install JTAG Driver  (CH347 / CH341)",
                    lambda: launch_file(app, d / "CH341SER.EXE", "CH341 driver installer")).pack(fill="x", padx=20, pady=(0, 18))
        EclipseArt(self).pack(fill="both", expand=True, pady=(12, 0))


class FlasherView(BaseView):
    def __init__(self, app, parent):
        super().__init__(app, parent, "Device Flasher", "Flash a custom firmware (.bin) to the FPGA configuration flash")
        self.runner = ProcessRunner(app)
        self.bin_path = ctk.StringVar()
        self.delete_after = ctk.BooleanVar(value=False)
        card = make_card(self)
        card.pack(fill="x")
        card_title(card, "Firmware flashing").pack(fill="x", padx=20, pady=(16, 8))
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=20, pady=(0, 8))
        ctk.CTkLabel(row, text="Target board", width=110, anchor="w", font=ctk.CTkFont(FONT, 13), text_color=MUTED).pack(side="left")
        self.board_menu = ctk.CTkOptionMenu(
            row, values=list(BOARD_LABELS.values()), command=self.on_menu, height=34, fg_color=BG_DEEP,
            button_color=CARD_HI, button_hover_color="#1c2132", dropdown_fg_color=CARD,
            dropdown_hover_color=CARD_HI, text_color=SILVER, font=ctk.CTkFont(FONT, 12),
        )
        self.board_menu.pack(side="left", fill="x", expand=True)
        row2 = ctk.CTkFrame(card, fg_color="transparent")
        row2.pack(fill="x", padx=20, pady=(0, 8))
        self.entry = ctk.CTkEntry(row2, textvariable=self.bin_path, height=36, fg_color=BG_DEEP, border_color=BORDER,
                                  placeholder_text="Select custom firmware (.bin) ...", text_color=SILVER, corner_radius=10)
        self.entry.pack(side="left", fill="x", expand=True)
        make_button(row2, "Browse .bin", self.browse, "normal", width=120, height=36).pack(side="left", padx=(10, 0))
        ctk.CTkCheckBox(card, text="Delete binary after successful flash", variable=self.delete_after,
                        font=ctk.CTkFont(FONT, 12), text_color=MUTED, fg_color=ACCENT_DIM, hover_color=ACCENT,
                        border_color=BORDER, checkmark_color="#eaf1ff").pack(anchor="w", padx=20, pady=(2, 12))
        self.flash_btn = make_button(card, "Flash Custom Firmware", self.flash, "glow")
        self.flash_btn.pack(fill="x", padx=20, pady=(0, 8))
        make_button(card, "Kill Flashing", self.runner.kill, "danger").pack(fill="x", padx=20, pady=(0, 18))
        EclipseArt(self).pack(fill="both", expand=True, pady=(12, 0))
        self.sync_menu()
        app.board_listeners.append(self.sync_menu)

    def sync_menu(self):
        self.board_menu.set(BOARD_LABELS[self.app.board_var.get()])

    def on_menu(self, label):
        self.app.select_board(label.split()[0])

    def browse(self):
        path = filedialog.askopenfilename(title="Select firmware", filetypes=[("Firmware", "*.bin"), ("All files", "*.*")])
        if path:
            self.bin_path.set(path)

    def flash(self):
        path = Path(self.bin_path.get().strip())
        board = self.app.board_var.get()
        if not path.is_file():
            self.app.log("Select a valid firmware (.bin) file first.", "WARN")
            return
        exe = find_openocd()
        if not exe:
            self.app.log("OpenOCD not found. Put it in tools/openocd/bin or add it to PATH.", "ERR")
            return
        flash_cfg = TOOLS / "cfg" / f"flash_{board}.cfg"
        if not flash_cfg.exists():
            self.app.log(f"Flash script missing: {flash_cfg}", "ERR")
            return
        iface = self.app.iface_var.get()
        iface_cfg = INTERFACES["CH347" if iface == "Auto" else iface]
        cmd = [exe, "-f", iface_cfg, "-f", str(flash_cfg), "-c", f'program "{path.as_posix()}" verify reset exit']
        self.flash_btn.configure(state="disabled")
        self.app.log(f"Flashing {path.name} to {board} ...")
        self.runner.start(cmd, lambda line: self.app.log(line, "INFO"), lambda code: self.done(code, path))

    def done(self, code, path):
        self.flash_btn.configure(state="normal")
        if code == 0:
            self.app.log("Flash completed successfully.", "OK")
            if self.delete_after.get():
                try:
                    path.unlink()
                    self.app.log("Firmware binary deleted.", "INFO")
                except OSError as exc:
                    self.app.log(f"Could not delete binary: {exc}", "WARN")
        else:
            self.app.log(f"Flashing stopped (exit code {code}).", "ERR")


class MakcuView(BaseView):
    def __init__(self, app, parent):
        super().__init__(app, parent, "Makcu", "Install the serial bridge driver and launch the Makcu AIO utility")
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="x")
        body.grid_columnconfigure((0, 1), weight=1, uniform="c")
        left, right = make_card(body), make_card(body)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        card_title(left, "Makcu driver").pack(fill="x", padx=20, pady=(16, 2))
        ctk.CTkLabel(left, text="Installs the WCH CH343 USB-to-UART driver.", font=ctk.CTkFont(FONT, 12),
                     text_color=MUTED, anchor="w").pack(fill="x", padx=20, pady=(0, 10))
        make_button(left, "Install Makcu Driver",
                    lambda: launch_file(app, TOOLS / "drivers" / "CH343SER.EXE", "CH343 driver installer")).pack(fill="x", padx=20, pady=(0, 18))
        card_title(right, "Makcu AIO utility").pack(fill="x", padx=20, pady=(16, 2))
        ctk.CTkLabel(right, text="Opens the standalone Makcu AIO control software.", font=ctk.CTkFont(FONT, 12),
                     text_color=MUTED, anchor="w").pack(fill="x", padx=20, pady=(0, 10))
        make_button(right, "Launch Makcu AIO",
                    lambda: launch_file(app, TOOLS / "makcu" / "MakcuAIO.exe", "Makcu AIO"), "glow").pack(fill="x", padx=20, pady=(0, 18))
        EclipseArt(self).pack(fill="both", expand=True, pady=(12, 0))


# ----------------------------------------------------------------------------- app
class MercureApp(ctk.CTk):
    NAV = [
        ("Auto-Detect", AutoDetectView),
        ("DNA Grabber", DNAView),
        ("Speed Test", SpeedTestView),
        ("Drivers", DriversView),
        ("Device Flasher", FlasherView),
        ("Makcu", MakcuView),
    ]

    def __init__(self):
        super().__init__(fg_color=BG)
        ctk.set_appearance_mode("dark")
        self.title(f"{APP_NAME} - v{APP_VERSION}")
        self.geometry("1000x650")
        self.minsize(900, 600)
        self.q = queue.Queue()
        self.board_var = ctk.StringVar(value="35T")
        self.iface_var = ctk.StringVar(value="Auto")
        self.board_listeners = []
        self.views, self.nav_buttons, self.board_buttons, self.current = {}, {}, {}, None

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.icon_planet = make_planet_icon(30)
        self.icon_discord = make_discord_icon(18)

        self.build_sidebar()
        self.build_main()
        enable_dark_titlebar(self)
        self.after(40, self.pump)
        self.show("Auto-Detect")
        self.startup_log()

    # ---- thread-safe plumbing
    def post(self, fn, *args):
        self.q.put((fn, args))

    def pump(self):
        try:
            while True:
                fn, args = self.q.get_nowait()
                fn(*args)
        except queue.Empty:
            pass
        self.after(40, self.pump)

    def log_threadsafe(self, msg, level="INFO"):
        self.post(self.log, msg, level)

    def log(self, msg, level="INFO"):
        stamp = time.strftime("[%H:%M:%S]")
        append_text(self.console_box, f"{stamp} [{level}] {msg}", level)

    # ---- layout
    def build_sidebar(self):
        side = ctk.CTkFrame(self, width=230, fg_color=SIDEBAR, corner_radius=0, border_width=0)
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        ctk.CTkFrame(side, width=1, fg_color=BORDER).place(relx=1, rely=0, relheight=1, anchor="ne")

        brand = ctk.CTkFrame(side, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 20))
        ctk.CTkLabel(brand, text="", image=self.icon_planet).pack(side="left")
        ctk.CTkLabel(brand, text="MERCURE TOOLS", font=ctk.CTkFont(FONT, 15, "bold"), text_color=SILVER).pack(side="left", padx=10)

        for name, _ in self.NAV:
            btn = ctk.CTkButton(
                side, text=name, anchor="w", height=40, corner_radius=10, border_width=1,
                fg_color="transparent", border_color=SIDEBAR, hover_color=CARD_HI, text_color=MUTED,
                font=ctk.CTkFont(FONT, 13, "bold"), command=lambda n=name: self.show(n),
            )
            btn.pack(fill="x", padx=14, pady=3)
            self.nav_buttons[name] = btn

        bottom = ctk.CTkFrame(side, fg_color=CARD, border_color=BORDER, border_width=1, corner_radius=12)
        bottom.pack(side="bottom", fill="x", padx=14, pady=16)
        ctk.CTkLabel(bottom, text="Board", font=ctk.CTkFont(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", padx=12, pady=(12, 4))
        row = ctk.CTkFrame(bottom, fg_color="transparent")
        row.pack(fill="x", padx=8)
        for b in BOARDS:
            btn = ctk.CTkButton(row, text=b, width=58, height=32, corner_radius=8, border_width=1,
                                font=ctk.CTkFont(FONT, 12, "bold"), command=lambda x=b: self.select_board(x))
            btn.pack(side="left", expand=True, padx=3)
            self.board_buttons[b] = btn
        ctk.CTkLabel(bottom, text="JTAG interface", font=ctk.CTkFont(FONT, 12), text_color=MUTED, anchor="w").pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkOptionMenu(
            bottom, values=["Auto", *INTERFACES], variable=self.iface_var, height=32, fg_color=BG_DEEP,
            button_color=CARD_HI, button_hover_color="#1c2132", dropdown_fg_color=CARD,
            dropdown_hover_color=CARD_HI, text_color=SILVER, font=ctk.CTkFont(FONT, 12),
        ).pack(fill="x", padx=12, pady=(0, 14))
        self.style_boards()

    def build_main(self):
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        top = ctk.CTkFrame(main, fg_color="transparent", height=34)
        top.grid(row=0, column=0, sticky="ew", padx=24, pady=(10, 0))
        self.hw_label = ctk.CTkLabel(top, text="●  NO HARDWARE CONNECTED", font=ctk.CTkFont(FONT, 11, "bold"), text_color=MUTED)
        self.hw_label.pack(side="right")

        self.content = ctk.CTkFrame(main, fg_color="transparent")
        self.content.grid(row=1, column=0, sticky="nsew", padx=24, pady=(4, 10))

        console = make_card(main)
        console.grid(row=2, column=0, sticky="ew", padx=24, pady=(0, 8))
        head = ctk.CTkFrame(console, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(10, 6))
        ctk.CTkLabel(head, text="System log", font=ctk.CTkFont(FONT, 12, "bold"), text_color=MUTED).pack(side="left")
        make_button(head, "Copy logs", self.copy_logs, "small", width=82).pack(side="right")
        make_button(head, "Clear", self.clear_logs, "small", width=60).pack(side="right", padx=6)
        self.console_box = make_log_box(console, height=118)
        self.console_box.pack(fill="x", padx=14, pady=(0, 14))

        footer = ctk.CTkFrame(main, fg_color=SIDEBAR, corner_radius=0, height=34)
        footer.grid(row=3, column=0, sticky="ew")
        link = ctk.CTkFrame(footer, fg_color="transparent", cursor="hand2")
        link.pack(pady=6)
        icon = ctk.CTkLabel(link, text="", image=self.icon_discord)
        icon.pack(side="left")
        text = ctk.CTkLabel(link, text=f"Join our Discord Community :  {DISCORD_URL}",
                            font=ctk.CTkFont(FONT, 12), text_color=ACCENT, cursor="hand2")
        text.pack(side="left", padx=8)
        for w in (link, icon, text):
            w.bind("<Button-1>", lambda e: webbrowser.open(DISCORD_URL))
        text.bind("<Enter>", lambda e: text.configure(text_color="#c4d7ff"))
        text.bind("<Leave>", lambda e: text.configure(text_color=ACCENT))

    # ---- behaviour
    def show(self, name):
        if self.current:
            self.views[self.current].pack_forget()
        if name not in self.views:
            cls = dict(self.NAV)[name]
            self.views[name] = cls(self, self.content)
        self.views[name].pack(fill="both", expand=True)
        self.views[name].on_show()
        self.current = name
        for n, btn in self.nav_buttons.items():
            active = n == name
            btn.configure(
                fg_color=ACCENT_BG if active else "transparent",
                border_color=ACCENT_DIM if active else SIDEBAR,
                text_color=SILVER if active else MUTED,
            )

    def style_boards(self):
        for b, btn in self.board_buttons.items():
            active = b == self.board_var.get()
            btn.configure(
                fg_color=ACCENT_BG if active else BG_DEEP,
                border_color=ACCENT if active else BORDER,
                text_color="#eaf1ff" if active else MUTED,
                hover_color="#1d2540",
            )

    def select_board(self, board):
        if board not in BOARDS:
            return
        changed = board != self.board_var.get()
        self.board_var.set(board)
        self.style_boards()
        for fn in self.board_listeners:
            fn()
        if changed:
            self.log(f"Board set to {board}.")

    def set_hardware(self, text, connected):
        self.hw_label.configure(text=f"●  {text.upper()}", text_color=OK if connected else MUTED)

    def copy_logs(self):
        self.clipboard_clear()
        self.clipboard_append(self.console_box.get("1.0", "end").strip())

    def clear_logs(self):
        self.console_box.configure(state="normal")
        self.console_box.delete("1.0", "end")
        self.console_box.configure(state="disabled")

    def startup_log(self):
        self.log(f"{APP_NAME} {APP_VERSION} ready. Hardware : 35T / 75T / 100T", "OK")
        exe = find_openocd()
        self.log(f"OpenOCD: {'found' if exe else 'not found (put it in tools/openocd/bin)'}", "INFO" if exe else "WARN")
        self.log(f"Tools folder: {TOOLS}")


if __name__ == "__main__":
    MercureApp().mainloop()
