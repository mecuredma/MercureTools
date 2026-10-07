"""
MercureTools - AIO pour cartes DMA FPGA (Artix-7 35T / 75T / 100T)
Backends :
  - pyftdi          -> détection IDCODE + lecture DNA via JTAG (FT2232H / FT232H / FT4232H)
  - openFPGALoader  -> flash du .bin (embarqué dans l'exe par le workflow GitHub)
  - leechcorepyc    -> speed test (nécessite FTD3XX.dll / carte active côté cible)
  - pyserial        -> gestion Makcu (CH343, commandes "km.*")
"""
import os
import sys
import time
import queue
import shutil
import threading
import subprocess
import webbrowser
from tkinter import filedialog

import customtkinter as ctk

APP_NAME = "MercureTools"
VERSION = "1.0.0"

# ---- Charte "Mercure" -------------------------------------------------------
BG = "#0a0e14"
PANEL = "#111823"
CARD = "#172131"
SILVER = "#c9d4e3"
ACCENT = "#38bdf8"
ACCENT_HOVER = "#0ea5e9"
OK = "#4ade80"
WARN = "#fbbf24"
ERR = "#f87171"

# ---- Données matériel -------------------------------------------------------
# IDCODE JTAG Artix-7 (masqué sur les 28 bits bas, la version est dans les 4 bits hauts)
IDCODES = {
    0x0362D093: "XC7A35T",
    0x03632093: "XC7A75T",
    0x03631093: "XC7A100T",
}
MODELS = {
    "35T": "xc7a35tfgg484",
    "75T": "xc7a75tfgg484",
    "100T": "xc7a100tfgg484",
}
# nom affiché -> (URL pyftdi, nom openFPGALoader)
CABLES = {
    "FT2232H": ("ftdi://ftdi:2232h/1", "ft2232"),
    "FT232H": ("ftdi://ftdi:232h/1", "ft232"),
    "FT4232H": ("ftdi://ftdi:4232h/1", "ft4232"),
}
LINKS = {
    "Zadig (WinUSB pour JTAG)": "https://zadig.akeo.ie/",
    "Pilotes FTDI (VCP/D2XX)": "https://ftdichip.com/drivers/",
    "Pilote WCH CH343 (Makcu)": "https://www.wch-ic.com/downloads/CH343SER_EXE.html",
}


def resource_path(rel):
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def find_ofl():
    p = resource_path(os.path.join("tools", "openFPGALoader.exe"))
    if os.path.isfile(p):
        return p
    return shutil.which("openFPGALoader")


def run_cmd(cmd, log):
    env = os.environ.copy()
    env["PATH"] = os.path.dirname(os.path.abspath(cmd[0])) + os.pathsep + env.get("PATH", "")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, errors="replace", env=env, creationflags=flags)
    for line in p.stdout:
        if line.strip():
            log(line.rstrip())
    return p.wait()


# ---- JTAG (pyftdi) ----------------------------------------------------------
def jtag_open(url):
    from pyftdi.jtag import JtagEngine, JtagTool
    eng = JtagEngine(trst=False, frequency=1e6)
    eng.configure(url)
    eng.reset()
    return eng, JtagTool(eng)


def jtag_idcode(cable_name):
    """Retourne (idcode, nom_cable) en essayant le câble choisi ou tous (Auto)."""
    names = list(CABLES) if cable_name == "Auto" else [cable_name]
    last = None
    for n in names:
        try:
            eng, tool = jtag_open(CABLES[n][0])
            try:
                code = tool.idcode()
            finally:
                eng.close()
            if code not in (0, 0xFFFFFFFF):
                return code, n
        except Exception as e:  # noqa
            last = e
    raise RuntimeError(f"Aucune interface JTAG FTDI trouvée ({last}). "
                       "Vérifie le driver WinUSB (onglet Drivers) et le câblage.")


def jtag_dna(cable_name):
    from pyftdi.bits import BitSequence
    names = list(CABLES) if cable_name == "Auto" else [cable_name]
    last = None
    for n in names:
        try:
            eng, tool = jtag_open(CABLES[n][0])
            try:
                eng.write_ir(BitSequence(0x17, length=6))  # ISC_DNA (7-series)
                raw = int(eng.read_dr(64))
                eng.go_idle()
                eng.reset()
            finally:
                eng.close()
            return raw
        except Exception as e:  # noqa
            last = e
    raise RuntimeError(f"Lecture DNA impossible ({last})")


# ---- Application ------------------------------------------------------------
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(f"{APP_NAME} v{VERSION}")
        self.geometry("1020x700")
        self.minsize(920, 620)
        self.configure(fg_color=BG)

        self.model = ctk.StringVar(value="35T")
        self.cable = ctk.StringVar(value="Auto")
        self.fw_path = ctk.StringVar()
        self.serial = None
        self.pages = {}

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self._build_sidebar()
        self._build_main()
        self.show("detect")
        self.log(f"{APP_NAME} {VERSION} prêt. Matériel : 35T / 75T / 100T")

    # --- utilitaires UI
    def ui(self, fn):
        self.after(0, fn)

    def log(self, msg, color=None):
        def _w():
            self.console.configure(state="normal")
            self.console.insert("end", time.strftime("[%H:%M:%S] ") + str(msg) + "\n")
            self.console.see("end")
            self.console.configure(state="disabled")
        self.ui(_w)

    def bg(self, fn, *args):
        def w():
            try:
                fn(*args)
            except Exception as e:  # noqa
                self.log(f"[ERREUR] {e}")
        threading.Thread(target=w, daemon=True).start()

    def btn(self, parent, text, cmd, **kw):
        return ctk.CTkButton(parent, text=text, command=cmd, fg_color=ACCENT,
                             hover_color=ACCENT_HOVER, text_color="#04121c",
                             font=ctk.CTkFont(weight="bold"), corner_radius=8, **kw)

    def card(self, page, title, subtitle=""):
        ctk.CTkLabel(page, text=title, font=ctk.CTkFont(size=24, weight="bold"),
                     text_color=SILVER).pack(anchor="w", padx=24, pady=(20, 0))
        if subtitle:
            ctk.CTkLabel(page, text=subtitle, text_color="#7f8da3").pack(anchor="w", padx=24, pady=(0, 10))
        c = ctk.CTkFrame(page, fg_color=CARD, corner_radius=12)
        c.pack(fill="x", padx=24, pady=8)
        return c

    def value_label(self, parent, label):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(row, text=label, width=150, anchor="w", text_color="#7f8da3").pack(side="left")
        v = ctk.CTkLabel(row, text="—", anchor="w", text_color=SILVER,
                         font=ctk.CTkFont(family="Consolas", size=14))
        v.pack(side="left", fill="x", expand=True)
        return v

    # --- structure
    def _build_sidebar(self):
        sb = ctk.CTkFrame(self, width=220, fg_color=PANEL, corner_radius=0)
        sb.grid(row=0, column=0, sticky="nsw")
        sb.grid_propagate(False)
        ctk.CTkLabel(sb, text="☿ MERCURE", font=ctk.CTkFont(size=22, weight="bold"),
                     text_color=ACCENT).pack(pady=(24, 0))
        ctk.CTkLabel(sb, text="T O O L S", text_color=SILVER,
                     font=ctk.CTkFont(size=12)).pack(pady=(0, 20))

        self.nav = {}
        for key, label in [("detect", "🔍  Auto-Detect"), ("dna", "🧬  DNA Grabber"),
                           ("speed", "⚡  Speed Test"), ("drivers", "🧩  Drivers"),
                           ("flash", "💾  Device Flasher"), ("makcu", "🖱  Makcu")]:
            b = ctk.CTkButton(sb, text=label, anchor="w", fg_color="transparent",
                              hover_color=CARD, text_color=SILVER, height=40,
                              command=lambda k=key: self.show(k))
            b.pack(fill="x", padx=12, pady=2)
            self.nav[key] = b

        ctk.CTkLabel(sb, text="Carte", text_color="#7f8da3").pack(anchor="w", padx=16, pady=(24, 0))
        ctk.CTkSegmentedButton(sb, values=list(MODELS), variable=self.model,
                               selected_color=ACCENT, selected_hover_color=ACCENT_HOVER
                               ).pack(fill="x", padx=12, pady=4)
        ctk.CTkLabel(sb, text="Interface JTAG", text_color="#7f8da3").pack(anchor="w", padx=16, pady=(10, 0))
        ctk.CTkOptionMenu(sb, values=["Auto"] + list(CABLES), variable=self.cable,
                          fg_color=CARD, button_color=ACCENT).pack(fill="x", padx=12, pady=4)

    def _build_main(self):
        main = ctk.CTkFrame(self, fg_color=BG, corner_radius=0)
        main.grid(row=0, column=1, sticky="nsew")
        main.grid_rowconfigure(0, weight=1)
        main.grid_columnconfigure(0, weight=1)

        self.container = ctk.CTkFrame(main, fg_color="transparent")
        self.container.grid(row=0, column=0, sticky="nsew")
        for key, fn in [("detect", self.page_detect), ("dna", self.page_dna),
                        ("speed", self.page_speed), ("drivers", self.page_drivers),
                        ("flash", self.page_flash), ("makcu", self.page_makcu)]:
            f = ctk.CTkFrame(self.container, fg_color="transparent")
            fn(f)
            self.pages[key] = f

        self.console = ctk.CTkTextbox(main, height=180, fg_color=PANEL, text_color=SILVER,
                                      font=ctk.CTkFont(family="Consolas", size=12), state="disabled")
        self.console.grid(row=1, column=0, sticky="ew", padx=24, pady=(0, 18))

    def show(self, key):
        for f in self.pages.values():
            f.pack_forget()
        self.pages[key].pack(fill="both", expand=True)
        for k, b in self.nav.items():
            b.configure(fg_color=CARD if k == key else "transparent")

    # --- 1. Auto-detect
    def page_detect(self, p):
        c = self.card(p, "Hardware Auto-Detect", "Détecte la puce Artix-7 via l'IDCODE JTAG")
        self.d_chip = self.value_label(c, "Puce")
        self.d_id = self.value_label(c, "IDCODE")
        self.d_cable = self.value_label(c, "Interface")
        self.d_match = self.value_label(c, "Carte sélectionnée")
        self.btn(c, "Lancer la détection", lambda: self.bg(self.do_detect), height=38
                 ).pack(anchor="w", padx=18, pady=14)

    def do_detect(self):
        self.log("Détection en cours…")
        code, cab = jtag_idcode(self.cable.get())
        chip = IDCODES.get(code & 0x0FFFFFFF, "Inconnue")
        sel = self.model.get()
        self.ui(lambda: (self.d_chip.configure(text=chip, text_color=OK if chip != "Inconnue" else ERR),
                         self.d_id.configure(text=f"0x{code:08X}"),
                         self.d_cable.configure(text=cab)))
        if chip != "Inconnue":
            det = chip.replace("XC7A", "")
            self.ui(lambda: (self.model.set(det),
                             self.d_match.configure(text=f"Auto-sélection : {det}", text_color=OK)))
        self.log(f"Puce détectée : {chip} (IDCODE 0x{code:08X}) via {cab}")

    # --- 2. DNA
    def page_dna(self, p):
        c = self.card(p, "DNA Grabber", "Lit le Device DNA (57 bits) de l'Artix-7 via JTAG (ISC_DNA)")
        self.dna57 = self.value_label(c, "DNA (57 bits)")
        self.dnaraw = self.value_label(c, "Brut (64 bits)")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(anchor="w", padx=18, pady=14)
        self.btn(row, "Récupérer le DNA", lambda: self.bg(self.do_dna), height=38).pack(side="left")
        self.btn(row, "Copier", self.copy_dna, height=38, width=90).pack(side="left", padx=10)

    def do_dna(self):
        raw = jtag_dna(self.cable.get())
        d57 = raw & ((1 << 57) - 1)
        self.ui(lambda: (self.dna57.configure(text=f"{d57:015X}", text_color=OK),
                         self.dnaraw.configure(text=f"{raw:016X}")))
        self.log(f"DNA : {d57:015X} (brut {raw:016X})")

    def copy_dna(self):
        t = self.dna57.cget("text")
        if t != "—":
            self.clipboard_clear()
            self.clipboard_append(t)
            self.log("DNA copié dans le presse-papiers.")

    # --- 3. Speed test
    def page_speed(self, p):
        c = self.card(p, "Speed Test", "Mesure débit & latence via LeechCore (carte active dans la cible)")
        self.s_thr = self.value_label(c, "Débit")
        self.s_lat = self.value_label(c, "Latence (4 KB)")
        self.s_ok = self.value_label(c, "Lectures OK")
        self.s_bar = ctk.CTkProgressBar(c, progress_color=ACCENT)
        self.s_bar.set(0)
        self.s_bar.pack(fill="x", padx=18, pady=(8, 0))
        self.btn(c, "Lancer le test", lambda: self.bg(self.do_speed), height=38
                 ).pack(anchor="w", padx=18, pady=14)

    def do_speed(self):
        try:
            from leechcorepyc import LeechCore
        except ImportError:
            raise RuntimeError("leechcorepyc indisponible dans ce build.")
        self.log("Ouverture du device FPGA (LeechCore)…")
        lc = LeechCore("fpga")
        try:
            addr, chunk, total = 0x1000, 0x100000, 64  # 64 x 1 MB
            ok, t0 = 0, time.perf_counter()
            for i in range(total):
                try:
                    lc.read(addr + i * chunk, chunk)
                    ok += 1
                except Exception:
                    pass
                self.ui(lambda v=(i + 1) / total: self.s_bar.set(v))
            dt = time.perf_counter() - t0
            mbs = ok * chunk / dt / 1048576
            lats = []
            for _ in range(200):
                t = time.perf_counter()
                try:
                    lc.read(addr, 0x1000)
                    lats.append((time.perf_counter() - t) * 1000)
                except Exception:
                    pass
            lat = sum(lats) / len(lats) if lats else float("nan")
            self.ui(lambda: (self.s_thr.configure(text=f"{mbs:.1f} MB/s", text_color=OK),
                             self.s_lat.configure(text=f"{lat:.3f} ms"),
                             self.s_ok.configure(text=f"{ok}/{total}")))
            self.log(f"Speed test : {mbs:.1f} MB/s, latence {lat:.3f} ms, {ok}/{total} OK")
        finally:
            lc.close()

    # --- 4. Drivers
    def page_drivers(self, p):
        c = self.card(p, "Driver Installation", "Cartes DMA (FTDI / WinUSB) et Makcu (WCH CH343)")
        ctk.CTkLabel(c, text="Installer depuis un dossier contenant des .inf (admin requis) :",
                     text_color="#7f8da3").pack(anchor="w", padx=18, pady=(14, 4))
        self.btn(c, "Choisir un dossier de pilotes…", self.install_inf, height=38
                 ).pack(anchor="w", padx=18, pady=(0, 10))
        ctk.CTkLabel(c, text="Télécharger les pilotes officiels :", text_color="#7f8da3"
                     ).pack(anchor="w", padx=18, pady=(10, 4))
        for name, url in LINKS.items():
            ctk.CTkButton(c, text=name, fg_color=PANEL, hover_color=BG, text_color=SILVER,
                          anchor="w", command=lambda u=url: webbrowser.open(u), height=34
                          ).pack(fill="x", padx=18, pady=3)
        ctk.CTkLabel(c, text="Astuce : pour le JTAG, remplace le driver de l'interface 0 du "
                             "FT2232H par WinUSB avec Zadig.", text_color=WARN, wraplength=640,
                     justify="left").pack(anchor="w", padx=18, pady=14)

    def install_inf(self):
        d = filedialog.askdirectory(title="Dossier de pilotes")
        if d:
            self.bg(self._pnputil, d)

    def _pnputil(self, d):
        if os.name != "nt":
            raise RuntimeError("pnputil n'existe que sous Windows.")
        self.log(f"Installation des pilotes depuis {d}…")
        rc = run_cmd(["pnputil", "/add-driver", os.path.join(d, "*.inf"), "/subdirs", "/install"], self.log)
        self.log("Pilotes installés." if rc == 0 else f"pnputil a retourné le code {rc} (lancer en admin ?)")

    # --- 5. Flasher
    def page_flash(self, p):
        c = self.card(p, "Device Flasher", "Flash d'un firmware .bin sur la SPI flash (via openFPGALoader)")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkEntry(row, textvariable=self.fw_path, placeholder_text="Fichier firmware .bin",
                     fg_color=PANEL).pack(side="left", fill="x", expand=True)
        self.btn(row, "Parcourir", self.pick_fw, width=100).pack(side="left", padx=(8, 0))
        row2 = ctk.CTkFrame(c, fg_color="transparent")
        row2.pack(fill="x", padx=18, pady=6)
        ctk.CTkLabel(row2, text="Référence FPGA :", text_color="#7f8da3").pack(side="left")
        self.part = ctk.CTkEntry(row2, width=190, fg_color=PANEL)
        self.part.insert(0, MODELS["35T"])
        self.part.pack(side="left", padx=8)
        self.verify = ctk.CTkCheckBox(row2, text="Vérifier", fg_color=ACCENT)
        self.verify.select()
        self.verify.pack(side="left", padx=10)
        self.model.trace_add("write", lambda *_: (self.part.delete(0, "end"),
                                                  self.part.insert(0, MODELS.get(self.model.get(), ""))))
        self.f_bar = ctk.CTkProgressBar(c, progress_color=ACCENT, mode="indeterminate")
        self.f_bar.pack(fill="x", padx=18, pady=8)
        self.f_bar.set(0)
        self.btn(c, "⚠ Flasher la carte", self.confirm_flash, height=40,
                 ).pack(anchor="w", padx=18, pady=14)

    def pick_fw(self):
        f = filedialog.askopenfilename(filetypes=[("Firmware", "*.bin"), ("Tous", "*.*")])
        if f:
            self.fw_path.set(f)

    def confirm_flash(self):
        fw = self.fw_path.get()
        if not fw or not os.path.isfile(fw):
            self.log("[ERREUR] Sélectionne un fichier .bin valide.")
            return
        self.bg(self.do_flash, fw, self.part.get().strip(), bool(self.verify.get()))

    def do_flash(self, fw, part, verify):
        ofl = find_ofl()
        if not ofl:
            raise RuntimeError("openFPGALoader introuvable (non embarqué dans ce build).")
        cab = self.cable.get()
        cab_ofl = CABLES["FT2232H" if cab == "Auto" else cab][1]
        cmd = [ofl, "-c", cab_ofl, "--fpga-part", part, "-f", fw, "-r"]
        if verify:
            cmd.insert(-1, "--verify")
        self.log("Flash : " + " ".join(cmd))
        self.ui(lambda: self.f_bar.start())
        try:
            rc = run_cmd(cmd, self.log)
        finally:
            self.ui(lambda: (self.f_bar.stop(), self.f_bar.set(0)))
        self.log("✔ Flash terminé." if rc == 0 else f"✘ Échec du flash (code {rc}).")

    # --- 6. Makcu
    def page_makcu(self, p):
        c = self.card(p, "Makcu Management", "Connexion série (CH343) et commandes de base")
        row = ctk.CTkFrame(c, fg_color="transparent")
        row.pack(fill="x", padx=18, pady=(14, 6))
        self.mk_port = ctk.CTkOptionMenu(row, values=["—"], fg_color=PANEL, button_color=ACCENT, width=300)
        self.mk_port.pack(side="left")
        self.btn(row, "↻", self.refresh_ports, width=40).pack(side="left", padx=6)
        self.mk_baud = ctk.CTkEntry(row, width=100, fg_color=PANEL)
        self.mk_baud.insert(0, "115200")
        self.mk_baud.pack(side="left", padx=6)
        self.mk_state = self.value_label(c, "État")
        self.mk_ver = self.value_label(c, "Version")
        r2 = ctk.CTkFrame(c, fg_color="transparent")
        r2.pack(anchor="w", padx=18, pady=6)
        for t, f in [("Connecter", self.mk_connect), ("Déconnecter", self.mk_disconnect),
                     ("Version", lambda: self.bg(self.mk_version)),
                     ("Test mouvement", lambda: self.bg(self.mk_test)),
                     ("Commande…", self.mk_custom)]:
            self.btn(r2, t, f, height=34).pack(side="left", padx=(0, 8))
        self.mk_cmd = ctk.CTkEntry(c, placeholder_text="ex: km.version()", fg_color=PANEL)
        self.mk_cmd.pack(fill="x", padx=18, pady=(4, 14))
        self.refresh_ports()

    def refresh_ports(self):
        try:
            from serial.tools import list_ports
            ports = []
            for pt in list_ports.comports():
                tag = " (CH343/Makcu?)" if pt.vid == 0x1A86 else ""
                ports.append(f"{pt.device} - {pt.description}{tag}")
            self.mk_port.configure(values=ports or ["Aucun port"])
            self.mk_port.set(next((x for x in ports if "Makcu" in x), ports[0] if ports else "Aucun port"))
        except Exception as e:  # noqa
            self.log(f"[ERREUR] {e}")

    def mk_connect(self):
        import serial
        port = self.mk_port.get().split(" ")[0]
        self.mk_disconnect()
        try:
            self.serial = serial.Serial(port, int(self.mk_baud.get()), timeout=0.5)
            self.mk_state.configure(text=f"Connecté ({port})", text_color=OK)
            self.log(f"Makcu connecté sur {port}")
        except Exception as e:  # noqa
            self.mk_state.configure(text="Erreur", text_color=ERR)
            self.log(f"[ERREUR] {e}")

    def mk_disconnect(self):
        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass
            self.serial = None
            self.mk_state.configure(text="Déconnecté", text_color=SILVER)

    def mk_send(self, cmd):
        if not self.serial or not self.serial.is_open:
            raise RuntimeError("Makcu non connecté.")
        self.serial.reset_input_buffer()
        self.serial.write((cmd + "\r\n").encode())
        time.sleep(0.15)
        resp = self.serial.read(self.serial.in_waiting or 1).decode(errors="replace").strip()
        self.log(f">> {cmd}" + (f"\n<< {resp}" if resp else ""))
        return resp

    def mk_version(self):
        r = self.mk_send("km.version()")
        self.ui(lambda: self.mk_ver.configure(text=r.splitlines()[-1] if r else "—"))

    def mk_test(self):
        self.mk_send("km.move(50,0)")
        time.sleep(0.2)
        self.mk_send("km.move(-50,0)")

    def mk_custom(self):
        c = self.mk_cmd.get().strip()
        if c:
            self.bg(self.mk_send, c)


if __name__ == "__main__":
    App().mainloop()
