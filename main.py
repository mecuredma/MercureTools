# -*- coding: utf-8 -*-
"""
MercureTools - DMA Firmware & Hardware Tools
Thème Eclipse / Spatial (noir pur + étoiles) - CustomTkinter

Les actions matérielles (détection, DNA, flash, drivers...) sont SIMULÉES
et affichées dans les logs. Remplace les méthodes marquées [SIM] par tes
vrais appels (subprocess OpenOCD, DLL, etc.) quand tu seras prêt.
"""

import os
import sys
import random
import datetime
import webbrowser
import tkinter as tk
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image

# --------------------------------------------------------------------------
# Constantes
# --------------------------------------------------------------------------
APP_NAME = "MercureTools"
APP_TITLE = "MercureTools — DMA Firmware & Hardware Tools"
APP_VERSION = "1.0"
DISCORD_URL = "https://discord.gg/UpywRnsTAA"

BLACK = "#000000"
BORDER = "#1b1b2a"
WHITE = "#f2f2f7"
GRAY = "#8a8a95"
DIM = "#5b5b68"
ACCENT = "#8b5cf6"
ACCENT_BG = "#120d22"
ACCENT_HOVER = "#1d1438"
CYAN = "#22d3ee"
GREEN = "#34d399"
RED = "#ef4444"
AMBER = "#fbbf24"
HOVER = "#10101a"

PAD = 28

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


def resource_path(relative_path):
    """Chemin compatible PyInstaller (--onefile) et exécution normale."""
    try:
        base_path = sys._MEIPASS  # type: ignore[attr-defined]
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)


# --------------------------------------------------------------------------
# Helpers UI
# --------------------------------------------------------------------------
def make_card(parent):
    return ctk.CTkFrame(
        parent,
        fg_color=BLACK,
        border_color=BORDER,
        border_width=1,
        corner_radius=14,
    )


def primary_btn(parent, text, command, **kw):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color=ACCENT_BG,
        hover_color=ACCENT_HOVER,
        border_color=ACCENT,
        border_width=2,
        text_color=WHITE,
        corner_radius=18,
        height=38,
        font=ctk.CTkFont(size=13, weight="bold"),
        **kw,
    )


def secondary_btn(parent, text, command, **kw):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color="#07070d",
        hover_color="#14141f",
        border_color=BORDER,
        border_width=2,
        text_color=WHITE,
        corner_radius=18,
        height=38,
        font=ctk.CTkFont(size=13, weight="bold"),
        **kw,
    )


def danger_btn(parent, text, command, **kw):
    return ctk.CTkButton(
        parent,
        text=text,
        command=command,
        fg_color="#14070a",
        hover_color="#260b10",
        border_color=RED,
        border_width=2,
        text_color="#fca5a5",
        corner_radius=18,
        height=34,
        font=ctk.CTkFont(size=12, weight="bold"),
        **kw,
    )


def card_title(parent, text, color=CYAN):
    return ctk.CTkLabel(
        parent,
        text=text,
        text_color=color,
        font=ctk.CTkFont(size=14, weight="bold"),
        anchor="w",
    )


def card_desc(parent, text):
    return ctk.CTkLabel(
        parent,
        text=text,
        text_color=GRAY,
        font=ctk.CTkFont(size=11),
        anchor="w",
        justify="left",
    )


# --------------------------------------------------------------------------
# Page avec fond étoilé
# --------------------------------------------------------------------------
class StarPage(ctk.CTkFrame):
    STAR_COLORS = ["#ffffff", "#cfd8ff", "#a9b8ff", "#8e8ea0", "#d9c8ff", "#5f6280"]

    def __init__(self, master, title, subtitle):
        super().__init__(master, fg_color=BLACK, corner_radius=0)
        self._seed = sum(ord(c) for c in title) * 31 + 7
        self._twinkle_items = []

        # Canvas d'étoiles placé derrière tous les widgets de la page
        self.stars = tk.Canvas(self, bg=BLACK, highlightthickness=0, bd=0)
        self.stars.place(x=0, y=0, relwidth=1, relheight=1)
        self.stars.bind("<Configure>", self._draw_stars)

        ctk.CTkLabel(
            self,
            text=title,
            text_color=WHITE,
            font=ctk.CTkFont(size=24, weight="bold"),
            anchor="w",
        ).pack(fill="x", padx=PAD, pady=(24, 0))
        ctk.CTkLabel(
            self,
            text=subtitle,
            text_color=GRAY,
            font=ctk.CTkFont(size=12),
            anchor="w",
        ).pack(fill="x", padx=PAD, pady=(2, 12))

        self.after(900, self._twinkle)

    def _draw_stars(self, event):
        rng = random.Random(self._seed)
        self.stars.delete("all")
        self._twinkle_items = []
        w, h = max(event.width, 1), max(event.height, 1)
        count = max(60, int(w * h / 4200))
        for _ in range(count):
            x = rng.randint(0, w)
            y = rng.randint(0, h)
            r = rng.choice([0.7, 0.9, 1.0, 1.0, 1.2, 1.6])
            color = rng.choice(self.STAR_COLORS)
            item = self.stars.create_oval(
                x - r, y - r, x + r, y + r, fill=color, outline=""
            )
            self._twinkle_items.append((item, color))
            if r >= 1.6 and rng.random() < 0.5:
                self.stars.create_line(x - 4, y, x + 4, y, fill="#3a3a55")
                self.stars.create_line(x, y - 4, x, y + 4, fill="#3a3a55")

    def _twinkle(self):
        try:
            if self._twinkle_items:
                for item, base in random.sample(
                    self._twinkle_items, min(8, len(self._twinkle_items))
                ):
                    color = random.choice([base, "#2a2a3d", base, "#ffffff"])
                    self.stars.itemconfigure(item, fill=color)
            self.after(700, self._twinkle)
        except tk.TclError:
            pass


# --------------------------------------------------------------------------
# Application principale
# --------------------------------------------------------------------------
class MercureTools(ctk.CTk):
    NAV_ITEMS = [
        "Auto-Detect",
        "DNA Grabber",
        "Speed Test",
        "Drivers",
        "Device Flasher",
        "Makcu",
    ]

    def __init__(self):
        super().__init__(fg_color=BLACK)
        self.title(APP_TITLE)
        self.geometry("1280x720")
        self.minsize(1100, 640)
        self.after(250, self._set_icon)

        # État interne
        self._jobs = {}
        self.pages = {}
        self.nav_buttons = {}
        self.current_page = None
        self.hw_connected = False
        self.jtag_on = False
        self.data_on = False
        self.fw_path = ""
        self.speed_running = False
        self.makcu_connected = False
        self.drivers = {
            "ftd3xx": {
                "name": "DATA Driver (FTDI FTD3XX)",
                "desc": "USB 3.0 high-speed data pipe used by the DMA board.",
                "installed": False,
            },
            "ch347": {
                "name": "JTAG Driver (WCH CH347 / CH341)",
                "desc": "USB-to-JTAG bridge used for flashing and DNA query.",
                "installed": False,
            },
            "ch343": {
                "name": "Makcu Driver (WCH CH343)",
                "desc": "USB-to-UART serial communications driver.",
                "installed": False,
            },
        }
        self.driver_status_labels = {}

        self._load_logo()
        self._build_layout()
        self._build_pages()
        self.show_page("Auto-Detect")

        self.log("Basic DLLs verified: 3/3 available (FTD3XX.dll, leechcore.dll, vmm.dll)")
        self.log("Driver packages initialized: OK")
        self.log("Flashing tools initialized: (OpenOCD: OK)")
        self.log(f"{APP_NAME} {APP_VERSION} Suite Initialized Successfully.", "OK")
        self.log("Hardware actions are running in SIMULATION mode.", "WARN")

    # ------------------------------------------------------------------
    # Icône / logo
    # ------------------------------------------------------------------
    def _set_icon(self):
        try:
            self.iconbitmap(resource_path("logo.ico"))
        except Exception:
            pass

    def _load_logo(self):
        self.logo_img = None
        try:
            img = Image.open(resource_path("logo.ico")).convert("RGBA")
            self.logo_img = ctk.CTkImage(light_image=img, dark_image=img, size=(30, 30))
        except Exception:
            self.logo_img = None

    # ------------------------------------------------------------------
    # Layout général
    # ------------------------------------------------------------------
    def _build_layout(self):
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=0)
        self.grid_columnconfigure(2, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---------------- Sidebar ----------------
        self.sidebar = ctk.CTkFrame(self, width=220, fg_color=BLACK, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(8, weight=1)

        ctk.CTkLabel(
            self.sidebar,
            text="MODULES",
            text_color=DIM,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).grid(row=0, column=0, padx=16, pady=(30, 14), sticky="ew")
        self.sidebar.grid_columnconfigure(0, weight=1)

        for i, name in enumerate(self.NAV_ITEMS, start=1):
            btn = ctk.CTkButton(
                self.sidebar,
                text=name,
                height=40,
                corner_radius=18,
                fg_color="transparent",
                hover_color=HOVER,
                border_width=2,
                border_color=BLACK,
                text_color=GRAY,
                font=ctk.CTkFont(size=13, weight="bold"),
                command=lambda n=name: self.show_page(n),
            )
            btn.grid(row=i, column=0, padx=14, pady=5, sticky="ew")
            self.nav_buttons[name] = btn

        discord_card = make_card(self.sidebar)
        discord_card.grid(row=9, column=0, padx=14, pady=16, sticky="ew")
        ctk.CTkLabel(
            discord_card,
            text="MercureDMA's Discord",
            text_color=GRAY,
            font=ctk.CTkFont(size=11, weight="bold"),
        ).pack(padx=12, pady=(14, 8))
        primary_btn(
            discord_card, "Join Discord", lambda: self.open_discord(), width=170
        ).pack(padx=12, pady=(0, 14))

        # Séparateur vertical
        ctk.CTkFrame(self, width=1, fg_color=BORDER, corner_radius=0).grid(
            row=0, column=1, sticky="ns"
        )

        # ---------------- Zone principale ----------------
        self.main = ctk.CTkFrame(self, fg_color=BLACK, corner_radius=0)
        self.main.grid(row=0, column=2, sticky="nsew")
        self.main.grid_columnconfigure(0, weight=1)
        self.main.grid_rowconfigure(1, weight=1)

        self._build_header()

        self.container = ctk.CTkFrame(self.main, fg_color=BLACK, corner_radius=0)
        self.container.grid(row=1, column=0, sticky="nsew")
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        self._build_footer()

    def _build_header(self):
        header = ctk.CTkFrame(self.main, height=60, fg_color=BLACK, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_propagate(False)
        header.grid_columnconfigure(1, weight=1)

        left = ctk.CTkFrame(header, fg_color=BLACK, corner_radius=0)
        left.grid(row=0, column=0, padx=(PAD, 0), pady=14, sticky="w")
        if self.logo_img is not None:
            ctk.CTkLabel(left, text="", image=self.logo_img).pack(side="left", padx=(0, 10))
        ctk.CTkLabel(
            left,
            text=APP_NAME,
            text_color=WHITE,
            font=ctk.CTkFont(size=16, weight="bold"),
        ).pack(side="left")

        right = ctk.CTkFrame(header, fg_color=BLACK, corner_radius=0)
        right.grid(row=0, column=2, padx=(0, PAD), pady=12, sticky="e")

        self.lbl_hw = ctk.CTkLabel(
            right, text="● NO HARDWARE CONNECTED", text_color=DIM,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.lbl_hw.pack(side="left", padx=14)
        self.lbl_jtag = ctk.CTkLabel(
            right, text="JTAG: OFF", text_color=DIM,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.lbl_jtag.pack(side="left", padx=14)
        self.lbl_data = ctk.CTkLabel(
            right, text="DATA: OFF", text_color=DIM,
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.lbl_data.pack(side="left", padx=14)
        primary_btn(right, "Refresh", self.refresh_status, width=110, height=34).pack(
            side="left", padx=(10, 0)
        )

        ctk.CTkFrame(self.main, height=1, fg_color=BORDER, corner_radius=0).grid(
            row=0, column=0, sticky="sew"
        )

    def _build_footer(self):
        footer = ctk.CTkFrame(self.main, fg_color=BLACK, corner_radius=0)
        footer.grid(row=2, column=0, sticky="ew", padx=PAD, pady=(8, 10))
        footer.grid_columnconfigure(0, weight=1)

        logcard = make_card(footer)
        logcard.grid(row=0, column=0, sticky="ew")
        logcard.grid_columnconfigure(0, weight=1)

        top = ctk.CTkFrame(logcard, fg_color=BLACK, corner_radius=0)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(10, 4))
        top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            top, text="SYSTEM TERMINAL LOGS", text_color=GRAY,
            font=ctk.CTkFont(size=11, weight="bold"), anchor="w",
        ).grid(row=0, column=0, sticky="w")
        secondary_btn(top, "Clear", self.clear_logs, width=70, height=26).grid(
            row=0, column=1, padx=4
        )
        secondary_btn(top, "Copy Logs", self.copy_logs, width=90, height=26).grid(
            row=0, column=2, padx=(4, 0)
        )

        self.log_box = ctk.CTkTextbox(
            logcard,
            height=130,
            fg_color=BLACK,
            text_color=GRAY,
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
            wrap="word",
        )
        self.log_box.grid(row=1, column=0, sticky="ew", padx=14, pady=(0, 12))
        self.log_box.tag_config("INFO", foreground=GRAY)
        self.log_box.tag_config("OK", foreground=GREEN)
        self.log_box.tag_config("WARN", foreground=AMBER)
        self.log_box.tag_config("ERROR", foreground=RED)
        self.log_box.configure(state="disabled")

        link = ctk.CTkLabel(
            footer,
            text=f"{APP_NAME} v{APP_VERSION}  •  Community Discord: {DISCORD_URL}",
            text_color=DIM,
            font=ctk.CTkFont(size=11),
            cursor="hand2",
            anchor="e",
        )
        link.grid(row=1, column=0, sticky="e", pady=(6, 0))
        link.bind("<Button-1>", lambda _e: self.open_discord())
        link.bind("<Enter>", lambda _e: link.configure(text_color=ACCENT))
        link.bind("<Leave>", lambda _e: link.configure(text_color=DIM))

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def show_page(self, name):
        page = self.pages.get(name)
        if page is None:
            return
        page.tkraise()
        self.current_page = name
        for n, btn in self.nav_buttons.items():
            if n == name:
                btn.configure(
                    fg_color=ACCENT_BG, border_color=ACCENT, text_color=WHITE
                )
            else:
                btn.configure(
                    fg_color="transparent", border_color=BLACK, text_color=GRAY
                )

    def open_discord(self):
        webbrowser.open(DISCORD_URL)
        self.log(f"Opening Discord invite: {DISCORD_URL}")

    # ------------------------------------------------------------------
    # Logs
    # ------------------------------------------------------------------
    def log(self, message, level="INFO"):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] [{level}] {message}\n"
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line, level)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def clear_logs(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def copy_logs(self):
        text = self.log_box.get("1.0", "end").strip()
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log("Logs copied to clipboard.", "OK")

    # ------------------------------------------------------------------
    # Séquences temporisées (thread-safe, tout tourne dans la boucle Tk)
    # ------------------------------------------------------------------
    def run_sequence(self, group, steps, done=None):
        self.cancel_group(group)
        total = 0
        ids = []
        for delay, fn in steps:
            total += delay
            ids.append(self.after(total, fn))
        if done is not None:
            ids.append(self.after(total + 50, done))
        self._jobs[group] = ids

    def cancel_group(self, group):
        for job in self._jobs.pop(group, []):
            try:
                self.after_cancel(job)
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Statut matériel (en-tête)
    # ------------------------------------------------------------------
    def set_status(self, hw=None, jtag=None, data=None):
        if hw is not None:
            self.hw_connected = hw
        if jtag is not None:
            self.jtag_on = jtag
        if data is not None:
            self.data_on = data
        if self.hw_connected:
            self.lbl_hw.configure(text="● HARDWARE CONNECTED", text_color=GREEN)
        else:
            self.lbl_hw.configure(text="● NO HARDWARE CONNECTED", text_color=DIM)
        self.lbl_jtag.configure(
            text="JTAG: ON" if self.jtag_on else "JTAG: OFF",
            text_color=GREEN if self.jtag_on else DIM,
        )
        self.lbl_data.configure(
            text="DATA: ON" if self.data_on else "DATA: OFF",
            text_color=GREEN if self.data_on else DIM,
        )

    def refresh_status(self):
        self.log("Refreshing hardware status...")
        jtag_ok = self.drivers["ch347"]["installed"] and self.hw_connected
        data_ok = self.drivers["ftd3xx"]["installed"] and self.hw_connected
        self.set_status(jtag=jtag_ok, data=data_ok)
        self.log(
            f"Status: hardware={'connected' if self.hw_connected else 'not connected'}, "
            f"JTAG={'ON' if jtag_ok else 'OFF'}, DATA={'ON' if data_ok else 'OFF'}"
        )

    # ------------------------------------------------------------------
    # Construction des pages
    # ------------------------------------------------------------------
    def _build_pages(self):
        builders = {
            "Auto-Detect": self._page_autodetect,
            "DNA Grabber": self._page_dna,
            "Speed Test": self._page_speed,
            "Drivers": self._page_drivers,
            "Device Flasher": self._page_flasher,
            "Makcu": self._page_makcu,
        }
        for name, builder in builders.items():
            page = builder()
            page.grid(row=0, column=0, sticky="nsew")
            self.pages[name] = page

    # ---------------------------- Auto-Detect ----------------------------
    def _page_autodetect(self):
        page = StarPage(
            self.container,
            "MercureTools Hardware Dashboard",
            "PCIe FPGA DMA Firmware & Diagnostics Tool",
        )

        card = make_card(page)
        card.pack(fill="x", padx=PAD, pady=(6, 12))
        card.grid_columnconfigure(0, weight=1)

        card_title(card, "AUTO-DETECT DMA HARDWARE").grid(
            row=0, column=0, padx=20, pady=(16, 2), sticky="w"
        )
        card_desc(
            card, "Queries configuration space & TAP ID and automatically detects your board."
        ).grid(row=1, column=0, padx=20, pady=(0, 10), sticky="w")

        self.chip_label = ctk.CTkLabel(
            card,
            text="DETECTED CHIP: [ Click Auto-Detect Below ]",
            text_color=GRAY,
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.chip_label.grid(row=2, column=0, padx=20, pady=(6, 16), sticky="w")

        self.btn_detect = primary_btn(
            card, "Auto-Detect DMA Device", self.auto_detect, width=220
        )
        self.btn_detect.grid(row=2, column=1, padx=20, pady=(6, 16), sticky="e")

        row = ctk.CTkFrame(page, fg_color=BLACK, corner_radius=0)
        row.pack(fill="x", padx=PAD, pady=(0, 12))
        row.grid_columnconfigure((0, 1), weight=1, uniform="cards")

        c1 = make_card(row)
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        card_title(c1, "⚡ JTAG Flasher Link", WHITE).pack(padx=18, pady=(14, 2), anchor="w")
        card_desc(
            c1, "Handles firmware flashing & DNA querying via WCH CH347 / FTDI controller."
        ).pack(padx=18, anchor="w")
        b1 = ctk.CTkFrame(c1, fg_color=BLACK, corner_radius=0)
        b1.pack(padx=18, pady=(10, 16), anchor="w")
        secondary_btn(b1, "DNA Grabber", lambda: self.show_page("DNA Grabber"), width=130).pack(
            side="left", padx=(0, 8)
        )
        secondary_btn(b1, "Firmware Flasher", lambda: self.show_page("Device Flasher"), width=150).pack(
            side="left"
        )

        c2 = make_card(row)
        c2.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        card_title(c2, "🚀 DMA Performance Link", WHITE).pack(padx=18, pady=(14, 2), anchor="w")
        card_desc(
            c2, "High-speed memory read/write acquisition via FTD3XX / LeechCore pipeline."
        ).pack(padx=18, anchor="w")
        b2 = ctk.CTkFrame(c2, fg_color=BLACK, corner_radius=0)
        b2.pack(padx=18, pady=(10, 16), anchor="w")
        primary_btn(b2, "Run Speed Test", lambda: self.show_page("Speed Test"), width=130).pack(
            side="left", padx=(0, 8)
        )
        secondary_btn(b2, "Drivers & Setup", lambda: self.show_page("Drivers"), width=140).pack(
            side="left"
        )
        return page

    def auto_detect(self):
        self.btn_detect.configure(state="disabled", text="Detecting...")
        self.chip_label.configure(text="DETECTED CHIP: [ scanning... ]", text_color=AMBER)

        def finish():
            self.chip_label.configure(
                text="DETECTED CHIP: Xilinx Artix-7 XC7A35T  (IDCODE 0x0362D093)",
                text_color=GREEN,
            )
            self.btn_detect.configure(state="normal", text="Auto-Detect DMA Device")
            self.set_status(
                hw=True,
                jtag=self.drivers["ch347"]["installed"],
                data=self.drivers["ftd3xx"]["installed"],
            )

        steps = [
            (0, lambda: self.log("[SIM] Starting auto-detection...")),
            (500, lambda: self.log("[SIM] Opening JTAG interface (OpenOCD)...")),
            (700, lambda: self.log("[SIM] Scanning JTAG chain...")),
            (700, lambda: self.log("[SIM] TAP found: xc7a.tap  IDCODE = 0x0362D093")),
            (500, lambda: self.log("[SIM] Reading PCIe configuration space...")),
            (600, lambda: self.log("Detected: Xilinx Artix-7 XC7A35T", "OK")),
        ]
        self.run_sequence("detect", steps, done=finish)

    # ---------------------------- DNA Grabber ----------------------------
    def _page_dna(self):
        page = StarPage(
            self.container,
            "Device DNA Extractor",
            "Query and isolate the hardware unique 57-bit Xilinx Device DNA via JTAG.",
        )
        card = make_card(page)
        card.pack(fill="x", padx=PAD, pady=(6, 12))
        card.grid_columnconfigure(0, weight=1)

        card_title(card, "EXTRACTED HARDWARE DNA").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(16, 8), sticky="w"
        )
        self.dna_entry = ctk.CTkEntry(
            card,
            height=42,
            fg_color=BLACK,
            border_color=BORDER,
            border_width=2,
            text_color=WHITE,
            corner_radius=10,
            font=ctk.CTkFont(family="Consolas", size=14),
        )
        self.dna_entry.grid(row=1, column=0, padx=(20, 8), pady=(0, 10), sticky="ew")
        self._set_dna_text("0x000000000000000 (Click 'Read Hardware DNA' Below)")

        secondary_btn(card, "Copy DNA", self.copy_dna, width=120).grid(
            row=1, column=1, padx=(0, 20), pady=(0, 10)
        )

        bottom = ctk.CTkFrame(card, fg_color=BLACK, corner_radius=0)
        bottom.grid(row=2, column=0, columnspan=2, padx=20, pady=(0, 16), sticky="w")
        self.btn_dna = primary_btn(bottom, "Read Hardware DNA", self.read_dna, width=190)
        self.btn_dna.pack(side="left")
        self.dna_status = ctk.CTkLabel(
            bottom, text="Status: Ready to query", text_color=GRAY, font=ctk.CTkFont(size=11)
        )
        self.dna_status.pack(side="left", padx=14)

        note = make_card(page)
        note.pack(fill="x", padx=PAD, pady=(0, 12))
        ctk.CTkLabel(
            note,
            text=(
                "Note: DNA extraction executes OpenOCD via JTAG. Ensure your JTAG cable (CH347) is connected.\n"
                "Device DNA values are uniquely burned into silicon and used for 1:1 firmware license binding."
            ),
            text_color=GRAY,
            font=ctk.CTkFont(size=11),
            justify="left",
            anchor="w",
        ).pack(padx=16, pady=12, anchor="w")
        return page

    def _set_dna_text(self, text):
        self.dna_entry.configure(state="normal")
        self.dna_entry.delete(0, "end")
        self.dna_entry.insert(0, text)
        self.dna_entry.configure(state="readonly")

    def read_dna(self):
        self.btn_dna.configure(state="disabled")
        self.dna_status.configure(text="Status: Querying...", text_color=AMBER)

        def finish():
            value = "0x{:015X}".format(random.getrandbits(57))
            self._set_dna_text(value)
            self.dna_status.configure(text="Status: DNA read successfully", text_color=GREEN)
            self.btn_dna.configure(state="normal")
            self.log(f"[SIM] Device DNA = {value}", "OK")

        steps = [
            (0, lambda: self.log("[SIM] Launching OpenOCD (JTAG DNA query)...")),
            (600, lambda: self.log("[SIM] Shifting JTAG instruction FUSE_DNA...")),
            (700, lambda: self.log("[SIM] Reading 57-bit DNA register...")),
        ]
        self.run_sequence("dna", steps, done=finish)

    def copy_dna(self):
        value = self.dna_entry.get()
        self.clipboard_clear()
        self.clipboard_append(value)
        self.log("DNA copied to clipboard.", "OK")

    # ----------------------------- Speed Test -----------------------------
    def _page_speed(self):
        page = StarPage(
            self.container,
            "DMA Speed & Throughput Benchmark",
            "Benchmark raw PCIe physical memory read/write speeds.",
        )
        wrap = ctk.CTkFrame(page, fg_color=BLACK, corner_radius=0)
        wrap.pack(fill="both", expand=True, padx=PAD, pady=(6, 12))
        wrap.grid_columnconfigure(0, weight=1, uniform="sp")
        wrap.grid_columnconfigure(1, weight=1, uniform="sp")
        wrap.grid_rowconfigure(0, weight=1)

        left = make_card(wrap)
        left.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        card_title(left, "BENCHMARK TOOL").pack(padx=18, pady=(16, 8), anchor="w")

        self.speed_tool = ctk.CTkSegmentedButton(
            left,
            values=["Speed Test A", "DMATestTool"],
            fg_color="#07070d",
            selected_color=ACCENT_BG,
            selected_hover_color=ACCENT_HOVER,
            unselected_color="#07070d",
            unselected_hover_color=HOVER,
            text_color=WHITE,
            font=ctk.CTkFont(size=12, weight="bold"),
            height=34,
        )
        self.speed_tool.set("Speed Test A")
        self.speed_tool.pack(fill="x", padx=18, pady=(0, 12))

        self.btn_speed = primary_btn(left, "Start Speed Benchmark", self.start_speed)
        self.btn_speed.pack(fill="x", padx=18, pady=(0, 8))
        self.btn_speed_stop = danger_btn(left, "Stop Test", self.stop_speed)
        self.btn_speed_stop.pack(fill="x", padx=18, pady=(0, 16))

        right = make_card(wrap)
        right.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        right.grid_rowconfigure(1, weight=1)
        right.grid_columnconfigure(0, weight=1)
        card_title(right, "LIVE BENCHMARK STREAM", WHITE).grid(
            row=0, column=0, padx=18, pady=(16, 8), sticky="w"
        )
        self.speed_box = ctk.CTkTextbox(
            right,
            fg_color=BLACK,
            text_color=GREEN,
            border_color=BORDER,
            border_width=1,
            corner_radius=8,
            font=ctk.CTkFont(family="Consolas", size=12),
        )
        self.speed_box.grid(row=1, column=0, padx=18, pady=(0, 16), sticky="nsew")
        self._speed_write(
            "=== MercureTools SPEED BENCHMARK READY ===\n"
            "Select benchmark tool and click 'Start Speed Benchmark'.\n",
            clear=True,
        )
        return page

    def _speed_write(self, text, clear=False):
        self.speed_box.configure(state="normal")
        if clear:
            self.speed_box.delete("1.0", "end")
        self.speed_box.insert("end", text)
        self.speed_box.see("end")
        self.speed_box.configure(state="disabled")

    def start_speed(self):
        if self.speed_running:
            return
        self.speed_running = True
        self._speed_samples = []
        self._speed_tick_n = 0
        self.btn_speed.configure(state="disabled")
        tool = self.speed_tool.get()
        self._speed_write(f"=== {tool} - benchmark started ===\n", clear=True)
        self.log(f"[SIM] Speed benchmark started ({tool}).")
        self._speed_tick()

    def _speed_tick(self):
        if not self.speed_running:
            return
        self._speed_tick_n += 1
        read = random.uniform(120.0, 165.0)
        write = random.uniform(110.0, 150.0)
        lat = random.uniform(95.0, 140.0)
        self._speed_samples.append((read, write))
        self._speed_write(
            f"[{self._speed_tick_n:03d}] READ {read:7.2f} MB/s | "
            f"WRITE {write:7.2f} MB/s | LAT {lat:6.1f} us\n"
        )
        self._jobs["speed"] = [self.after(600, self._speed_tick)]

    def stop_speed(self):
        if not self.speed_running:
            return
        self.speed_running = False
        self.cancel_group("speed")
        self.btn_speed.configure(state="normal")
        if self._speed_samples:
            avg_r = sum(s[0] for s in self._speed_samples) / len(self._speed_samples)
            avg_w = sum(s[1] for s in self._speed_samples) / len(self._speed_samples)
            self._speed_write(
                f"=== Stopped. Average READ {avg_r:.2f} MB/s | WRITE {avg_w:.2f} MB/s ===\n"
            )
            self.log(
                f"[SIM] Benchmark stopped. Avg READ {avg_r:.2f} MB/s, WRITE {avg_w:.2f} MB/s.", "OK"
            )
        else:
            self._speed_write("=== Stopped. ===\n")
            self.log("[SIM] Benchmark stopped.")

    # ------------------------------ Drivers ------------------------------
    def _page_drivers(self):
        page = StarPage(
            self.container,
            "Drivers Setup & Status",
            "Install USB DATA / JTAG drivers and verify their status.",
        )
        card = make_card(page)
        card.pack(fill="x", padx=PAD, pady=(6, 12))
        card.grid_columnconfigure(0, weight=1)

        head = ctk.CTkFrame(card, fg_color=BLACK, corner_radius=0)
        head.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 6))
        head.grid_columnconfigure(0, weight=1)
        card_title(head, "HARDWARE DRIVERS").grid(row=0, column=0, sticky="w")
        secondary_btn(head, "Verify All", self.verify_all_drivers, width=110, height=30).grid(
            row=0, column=1
        )

        for i, (key, info) in enumerate(self.drivers.items(), start=1):
            row = ctk.CTkFrame(
                card, fg_color="#05050a", border_color=BORDER, border_width=1, corner_radius=12
            )
            row.grid(row=i, column=0, sticky="ew", padx=20, pady=6)
            row.grid_columnconfigure(0, weight=1)

            ctk.CTkLabel(
                row, text=info["name"], text_color=WHITE,
                font=ctk.CTkFont(size=13, weight="bold"), anchor="w",
            ).grid(row=0, column=0, padx=16, pady=(10, 0), sticky="w")
            ctk.CTkLabel(
                row, text=info["desc"], text_color=GRAY,
                font=ctk.CTkFont(size=11), anchor="w",
            ).grid(row=1, column=0, padx=16, pady=(0, 10), sticky="w")

            lbl = ctk.CTkLabel(
                row, text="NOT VERIFIED", text_color=DIM,
                font=ctk.CTkFont(size=11, weight="bold"), width=110,
            )
            lbl.grid(row=0, column=1, rowspan=2, padx=8)
            self.driver_status_labels[key] = lbl

            secondary_btn(
                row, "Verify", lambda k=key: self.verify_driver(k), width=80, height=30
            ).grid(row=0, column=2, rowspan=2, padx=4)
            primary_btn(
                row, "Install", lambda k=key: self.install_driver(k), width=90, height=30
            ).grid(row=0, column=3, rowspan=2, padx=(4, 16), pady=10)

        ctk.CTkFrame(card, height=10, fg_color=BLACK, corner_radius=0).grid(
            row=len(self.drivers) + 1, column=0
        )
        return page

    def _driver_label(self, key):
        lbl = self.driver_status_labels.get(key)
        if lbl is None:
            return
        if self.drivers[key]["installed"]:
            lbl.configure(text="INSTALLED", text_color=GREEN)
        else:
            lbl.configure(text="NOT INSTALLED", text_color=RED)

    def verify_driver(self, key):
        info = self.drivers[key]
        self.log(f"[SIM] Verifying {info['name']}...")

        def result():
            self._driver_label(key)
            if info["installed"]:
                self.log(f"{info['name']}: installed and ready.", "OK")
            else:
                self.log(f"{info['name']}: not installed.", "WARN")

        self.run_sequence(f"verify_{key}", [(500, lambda: None)], done=result)

    def verify_all_drivers(self):
        self.log("[SIM] Verifying all drivers...")
        for idx, key in enumerate(self.drivers):
            self.after(300 * (idx + 1), lambda k=key: self.verify_driver(k))

    def install_driver(self, key):
        info = self.drivers[key]
        if info["installed"]:
            self.log(f"{info['name']} is already installed.", "WARN")
            return

        def finish():
            info["installed"] = True
            self._driver_label(key)
            self.log(f"{info['name']} installed successfully.", "OK")
            self.refresh_status()

        steps = [
            (0, lambda: self.log(f"[SIM] Launching installer for {info['name']}...")),
            (700, lambda: self.log("[SIM] Extracting driver package...")),
            (800, lambda: self.log("[SIM] Registering driver with Windows (pnputil)...")),
        ]
        self.run_sequence(f"install_{key}", steps, done=finish)

    # --------------------------- Device Flasher ---------------------------
    def _page_flasher(self):
        page = StarPage(
            self.container,
            "Device Flasher",
            "Flash a custom firmware (.bit / .mcs) to the FPGA flash memory.",
        )
        card = make_card(page)
        card.pack(fill="x", padx=PAD, pady=(6, 12))
        card.grid_columnconfigure(1, weight=1)

        card_title(card, "FIRMWARE FLASHING").grid(
            row=0, column=0, columnspan=3, padx=20, pady=(16, 10), sticky="w"
        )

        ctk.CTkLabel(
            card, text="Target Board:", text_color=GRAY, font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=1, column=0, padx=(20, 10), pady=6, sticky="w")
        self.board_menu = ctk.CTkOptionMenu(
            card,
            values=["XC7A35T (Artix-7 35T)", "XC7A75T (Artix-7 75T)", "XC7A100T (Artix-7 100T)"],
            fg_color="#07070d",
            button_color="#14141f",
            button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#07070d",
            dropdown_hover_color=ACCENT_HOVER,
            text_color=WHITE,
            corner_radius=10,
            height=34,
        )
        self.board_menu.set("XC7A35T (Artix-7 35T)")
        self.board_menu.grid(row=1, column=1, columnspan=2, padx=(0, 20), pady=6, sticky="ew")

        ctk.CTkLabel(
            card, text="Firmware:", text_color=GRAY, font=ctk.CTkFont(size=12, weight="bold")
        ).grid(row=2, column=0, padx=(20, 10), pady=6, sticky="w")
        self.path_label = ctk.CTkLabel(
            card,
            text="Select custom firmware (.bit / .mcs) ...",
            text_color=DIM,
            fg_color="#05050a",
            corner_radius=10,
            height=36,
            anchor="w",
            padx=14,
        )
        self.path_label.grid(row=2, column=1, padx=(0, 8), pady=6, sticky="ew")
        secondary_btn(card, "Browse...", self.browse_firmware, width=120, height=36).grid(
            row=2, column=2, padx=(0, 20), pady=6
        )

        self.flash_progress = ctk.CTkProgressBar(
            card, height=8, fg_color="#0c0c14", progress_color=ACCENT, corner_radius=6
        )
        self.flash_progress.set(0)
        self.flash_progress.grid(row=3, column=0, columnspan=3, padx=20, pady=(14, 4), sticky="ew")
        self.flash_status = ctk.CTkLabel(
            card, text="Status: Idle", text_color=GRAY, font=ctk.CTkFont(size=11), anchor="w"
        )
        self.flash_status.grid(row=4, column=0, columnspan=3, padx=20, pady=(0, 8), sticky="w")

        self.btn_flash = primary_btn(card, "Flash Device Now", self.flash_now)
        self.btn_flash.grid(row=5, column=0, columnspan=3, padx=20, pady=(4, 8), sticky="ew")
        danger_btn(card, "Kill Flashing", self.kill_flash).grid(
            row=6, column=0, columnspan=3, padx=20, pady=(0, 18), sticky="ew"
        )
        return page

    def browse_firmware(self):
        path = filedialog.askopenfilename(
            title="Select firmware",
            filetypes=[
                ("FPGA firmware", "*.bit *.mcs"),
                ("Bitstream", "*.bit"),
                ("MCS file", "*.mcs"),
                ("All files", "*.*"),
            ],
        )
        if not path:
            self.log("Firmware selection cancelled.", "WARN")
            return
        self.fw_path = path
        name = os.path.basename(path)
        self.path_label.configure(text=path, text_color=WHITE)
        self.log(f"Firmware selected: {name}", "OK")

    def flash_now(self):
        if not self.fw_path:
            self.log("No firmware selected. Click Browse first.", "ERROR")
            self.flash_status.configure(text="Status: No firmware selected", text_color=RED)
            return
        if not os.path.isfile(self.fw_path):
            self.log(f"File not found: {self.fw_path}", "ERROR")
            self.flash_status.configure(text="Status: File not found", text_color=RED)
            return
        ext = os.path.splitext(self.fw_path)[1].lower()
        if ext not in (".bit", ".mcs"):
            self.log(f"Unsupported file type '{ext}'. Use .bit or .mcs.", "ERROR")
            self.flash_status.configure(text="Status: Unsupported file", text_color=RED)
            return

        board = self.board_menu.get()
        size = os.path.getsize(self.fw_path)
        self.btn_flash.configure(state="disabled", text="Flashing...")
        self.flash_progress.set(0)
        self.flash_status.configure(text="Status: Flashing...", text_color=AMBER)

        steps = [
            (0, lambda: self.log(f"[SIM] Target board: {board}")),
            (400, lambda: self.log(
                f"[SIM] Firmware: {os.path.basename(self.fw_path)} ({size:,} bytes)")),
            (500, lambda: self.log("[SIM] Initializing OpenOCD JTAG session...")),
            (700, lambda: self.log("[SIM] Erasing flash sector(s)...")),
        ]
        for pct in range(10, 101, 10):
            steps.append((260, lambda p=pct: self._flash_progress(p)))
        steps.append((500, lambda: self.log("[SIM] Verifying flash content...")))
        self.run_sequence("flash", steps, done=self._flash_done)

    def _flash_progress(self, pct):
        self.flash_progress.set(pct / 100.0)
        self.flash_status.configure(text=f"Status: Programming... {pct}%", text_color=AMBER)
        if pct % 30 == 0:
            self.log(f"[SIM] Programming... {pct}%")

    def _flash_done(self):
        self.flash_progress.set(1.0)
        self.flash_status.configure(text="Status: Flash completed", text_color=GREEN)
        self.btn_flash.configure(state="normal", text="Flash Device Now")
        self.log("[SIM] Flash completed successfully.", "OK")

    def kill_flash(self):
        self.cancel_group("flash")
        self.flash_progress.set(0)
        self.flash_status.configure(text="Status: Flashing aborted", text_color=RED)
        self.btn_flash.configure(state="normal", text="Flash Device Now")
        self.log("Flashing process killed by user.", "WARN")

    # ------------------------------- Makcu -------------------------------
    def _page_makcu(self):
        page = StarPage(
            self.container,
            "Makcu Hardware Tools",
            "Control Makcu USB interface hardware, install serial bridge drivers, and configure Makcu AIO.",
        )
        row = ctk.CTkFrame(page, fg_color=BLACK, corner_radius=0)
        row.pack(fill="x", padx=PAD, pady=(6, 12))
        row.grid_columnconfigure((0, 1), weight=1, uniform="mk")

        # Driver
        c1 = make_card(row)
        c1.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        card_title(c1, "MAKCU DRIVER").pack(padx=20, pady=(16, 2), anchor="w")
        card_desc(c1, "Installs WCH CH343 USB-to-UART serial communications driver.").pack(
            padx=20, anchor="w"
        )
        primary_btn(c1, "Install Makcu Driver", lambda: self.install_driver("ch343")).pack(
            fill="x", padx=20, pady=(14, 18)
        )

        # AIO config
        c2 = make_card(row)
        c2.grid(row=0, column=1, padx=(8, 0), sticky="nsew")
        c2.grid_columnconfigure(1, weight=1)
        card_title(c2, "MAKCU AIO CONFIGURATION").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(16, 2), sticky="w"
        )
        card_desc(c2, "Select the serial port and baud rate, then connect.").grid(
            row=1, column=0, columnspan=2, padx=20, sticky="w"
        )

        ctk.CTkLabel(c2, text="COM Port:", text_color=GRAY,
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=2, column=0, padx=(20, 10), pady=(12, 4), sticky="w")
        self.com_menu = ctk.CTkOptionMenu(
            c2, values=["COM3", "COM4", "COM5", "COM6"],
            fg_color="#07070d", button_color="#14141f", button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#07070d", dropdown_hover_color=ACCENT_HOVER,
            text_color=WHITE, corner_radius=10, height=32,
        )
        self.com_menu.grid(row=2, column=1, padx=(0, 20), pady=(12, 4), sticky="ew")

        ctk.CTkLabel(c2, text="Baud Rate:", text_color=GRAY,
                     font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=3, column=0, padx=(20, 10), pady=4, sticky="w")
        self.baud_menu = ctk.CTkOptionMenu(
            c2, values=["115200", "921600", "4000000"],
            fg_color="#07070d", button_color="#14141f", button_hover_color=ACCENT_HOVER,
            dropdown_fg_color="#07070d", dropdown_hover_color=ACCENT_HOVER,
            text_color=WHITE, corner_radius=10, height=32,
        )
        self.baud_menu.set("4000000")
        self.baud_menu.grid(row=3, column=1, padx=(0, 20), pady=4, sticky="ew")

        self.sw_passthrough = ctk.CTkSwitch(
            c2, text="USB passthrough", text_color=GRAY, progress_color=ACCENT,
            button_color=WHITE, fg_color="#14141f",
        )
        self.sw_passthrough.select()
        self.sw_passthrough.grid(row=4, column=0, columnspan=2, padx=20, pady=(8, 2), sticky="w")
        self.sw_echo = ctk.CTkSwitch(
            c2, text="Serial echo", text_color=GRAY, progress_color=ACCENT,
            button_color=WHITE, fg_color="#14141f",
        )
        self.sw_echo.grid(row=5, column=0, columnspan=2, padx=20, pady=(2, 8), sticky="w")

        self.makcu_status = ctk.CTkLabel(
            c2, text="Status: Disconnected", text_color=GRAY, font=ctk.CTkFont(size=11), anchor="w"
        )
        self.makcu_status.grid(row=6, column=0, columnspan=2, padx=20, pady=(0, 6), sticky="w")

        self.btn_makcu_connect = primary_btn(c2, "Connect", self.toggle_makcu)
        self.btn_makcu_connect.grid(row=7, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="ew")
        secondary_btn(c2, "Apply Config", self.apply_makcu).grid(
            row=8, column=0, columnspan=2, padx=20, pady=(0, 8), sticky="ew"
        )
        secondary_btn(c2, "Launch Makcu AIO", self.launch_makcu).grid(
            row=9, column=0, columnspan=2, padx=20, pady=(0, 18), sticky="ew"
        )
        return page

    def toggle_makcu(self):
        if not self.makcu_connected:
            port = self.com_menu.get()
            baud = self.baud_menu.get()
            self.log(f"[SIM] Opening {port} @ {baud} baud...")

            def done():
                self.makcu_connected = True
                self.makcu_status.configure(text=f"Status: Connected on {port}", text_color=GREEN)
                self.btn_makcu_connect.configure(text="Disconnect")
                self.log(f"Makcu connected on {port}.", "OK")

            self.run_sequence("makcu", [(700, lambda: None)], done=done)
        else:
            self.makcu_connected = False
            self.makcu_status.configure(text="Status: Disconnected", text_color=GRAY)
            self.btn_makcu_connect.configure(text="Connect")
            self.log("Makcu disconnected.", "WARN")

    def apply_makcu(self):
        if not self.makcu_connected:
            self.log("Connect the Makcu first.", "ERROR")
            return
        self.log(
            f"[SIM] Config applied: passthrough={'ON' if self.sw_passthrough.get() else 'OFF'}, "
            f"echo={'ON' if self.sw_echo.get() else 'OFF'}, baud={self.baud_menu.get()}",
            "OK",
        )

    def launch_makcu(self):
        self.log("[SIM] Launching Makcu AIO utility...")
        self.after(600, lambda: self.log("Makcu AIO utility started.", "OK"))


if __name__ == "__main__":
    app = MercureTools()
    app.mainloop()
