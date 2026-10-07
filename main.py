import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk

# Configuration globale de CustomTkinter
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("dark-blue")

def resource_path(relative_path):
    """ Gère les chemins des ressources pour PyInstaller (mode bundle ou normal) """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class MercureToolsApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MercureTools - v1.0.0")
        self.geometry("1280x720")  # CORRIGÉ : Utilisation de 'x' au lieu de '-'
        self.minsize(1050, 650)

        # Fond noir pur absolu
        self.configure(fg_color="#000000")

        # Chargement sécurisé de l'icône
        icon_path = resource_path("logo.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        # Configuration de la grille principale
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # --- SIDEBAR DE NAVIGATION ---
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#050505", border_width=1, border_color="#151515")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(7, weight=1)

        self.logo_label = ctk.CTkLabel(
            self.sidebar_frame, 
            text="MERCURE TOOLS", 
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#FFFFFF"
        )
        self.logo_label.grid(row=0, column=0, padx=20, pady=(25, 20), sticky="w")

        self.nav_buttons = {}
        nav_items = ["Auto-Detect", "DNA Grabber", "Speed Test", "Drivers", "Device Flasher", "Makcu"]
        
        for i, item in enumerate(nav_items, start=1):
            btn = ctk.CTkButton(
                self.sidebar_frame, 
                text=item, 
                fg_color="transparent", 
                text_color="#888888",
                hover_color="#121212",
                anchor="w",
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=lambda name=item: self.select_frame(name)
            )
            btn.grid(row=i, column=0, sticky="ew", padx=12, pady=3)
            self.nav_buttons[item] = btn

        # --- ZONE PRINCIPALE ---
        self.main_container = ctk.CTkFrame(self, fg_color="#000000", corner_radius=0)
        self.main_container.grid(row=0, column=1, sticky="nsew")
        self.main_container.grid_rowconfigure(0, weight=1)
        self.main_container.grid_columnconfigure(0, weight=1)

        self.frames = {}
        self.create_auto_detect_frame()
        self.create_dna_grabber_frame()
        self.create_speed_test_frame()
        self.create_drivers_frame()
        self.create_device_flasher_frame()
        self.create_makcu_frame()

        # Footer (Log & Discord)
        self.footer_frame = ctk.CTkFrame(self.main_container, fg_color="#030303", height=140, corner_radius=0, border_width=1, border_color="#121212")
        self.footer_frame.place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)
        
        self.discord_label = ctk.CTkLabel(
            self.footer_frame, 
            text="💬 Join our Discord Community : https://discord.gg/UpywRn5TAA", 
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#3b82f6"
        )
        self.discord_label.pack(side="top", pady=4)

        self.log_box = ctk.CTkTextbox(self.footer_frame, fg_color="#000000", text_color="#aaaaaa", font=ctk.CTkFont(family="Consolas", size=11), border_width=1, border_color="#151515")
        self.log_box.pack(fill="both", expand=True, padx=10, pady=(2, 8))
        self.log_box.insert("0.1", "[INFO] MercureTools initialized successfully in minimalist black mode.\n[INFO] Ready for hardware operations.\n")

        self.select_frame("Auto-Detect")

    def select_frame(self, name):
        for tab_name, btn in self.nav_buttons.items():
            if tab_name == name:
                btn.configure(fg_color="#101010", text_color="#FFFFFF")
            else:
                btn.configure(fg_color="transparent", text_color="#888888")
        self.frames[name].tkraise()

    def create_auto_detect_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="#000000", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(frame, text="Hardware Auto-Detect", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="nw", padx=30, pady=(25, 5))
        ctk.CTkLabel(frame, text="Detect the Artix-7 chip via the IDCODE JTAG", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#777777").pack(anchor="nw", padx=30, pady=(0, 15))
        
        card = ctk.CTkFrame(frame, fg_color="#060606", border_width=1, border_color="#181818", corner_radius=8)
        card.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(card, text="Chip:  -", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#CCCCCC").pack(anchor="w", padx=20, pady=10)
        ctk.CTkLabel(card, text="IDCODE:  -", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#CCCCCC").pack(anchor="w", padx=20, pady=10)
        ctk.CTkButton(card, text="Start Detection", fg_color="#181818", hover_color="#262626", text_color="#FFFFFF", command=lambda: self.log_box.insert("end", "[INFO] Running JTAG Auto-detect...\n")).pack(anchor="w", padx=20, pady=(10, 20))
        self.frames["Auto-Detect"] = frame

    def create_dna_grabber_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="#000000", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(frame, text="DNA Grabber", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="nw", padx=30, pady=(25, 5))
        card = ctk.CTkFrame(frame, fg_color="#060606", border_width=1, border_color="#181818", corner_radius=8)
        card.pack(fill="x", padx=30, pady=10)
        ctk.CTkButton(card, text="Read Device DNA", fg_color="#181818", hover_color="#262626", text_color="#FFFFFF", command=lambda: self.log_box.insert("end", "[INFO] Reading device DNA registers...\n")).pack(anchor="w", padx=20, pady=20)
        self.frames["DNA Grabber"] = frame

    def create_speed_test_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="#000000", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(frame, text="Speed Test", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="nw", padx=30, pady=(25, 5))
        card = ctk.CTkFrame(frame, fg_color="#060606", border_width=1, border_color="#181818", corner_radius=8)
        card.pack(fill="x", padx=30, pady=10)
        ctk.CTkButton(card, text="Run Performance Test", fg_color="#181818", hover_color="#262626", text_color="#FFFFFF", command=lambda: self.log_box.insert("end", "[INFO] Speed test execution started...\n")).pack(anchor="w", padx=20, pady=20)
        self.frames["Speed Test"] = frame

    def create_drivers_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="#000000", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(frame, text="Driver Management", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="nw", padx=30, pady=(25, 5))
        card = ctk.CTkFrame(frame, fg_color="#060606", border_width=1, border_color="#181818", corner_radius=8)
        card.pack(fill="x", padx=30, pady=10)
        ctk.CTkLabel(card, text="Status: Drivers up to date", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#888888").pack(anchor="w", padx=20, pady=20)
        self.frames["Drivers"] = frame

    def create_device_flasher_frame(self):
        frame = ctk.CTkFrame(self.main_container, fg_color="#000000", corner_radius=0)
        frame.grid(row=0, column=0, sticky="nsew")
        ctk.CTkLabel(frame, text="Device Flasher", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="#FFFFFF").pack(anchor="nw", padx=30, pady=(25, 5))
        ctk.CTkLabel(frame, text="Flash bitstreams and update device firmware safely.", font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#777777").pack(anchor="nw", padx=30, pady=(0, 15))

        card = ctk.CTkFrame(frame, fg_color="#060606", border_width=1, border_color="#181818", corner_radius=8)
        card.pack(fill="x", padx=30, pady=10)

        self.file_path_var = ctk.StringVar(value="No file selected...")
        ctk.CTkLabel(card, textvariable=self.file_path_var, font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#888888").pack(anchor="w", padx=20, pady=(15, 5))

        def browse_file():
            filename = filedialog.askopenfilename(title="Select Firmware File", filetypes=[("Bitstream files", "*.bit *.mcs"), ("All files", "*.*")])
            if filename:
                self.file_path_var.set(filename)
                self.log_box.insert("end", f"[INFO] Selected firmware: {filename}\n")

        ctk.CTkButton(card, text="Browse Firmware (.bit / .mcs)", fg_color="#181818", hover_color="#262626", text_color="#FFFFFF", command=browse_file).pack(anchor="w", padx=20, pady=5)

        def start_flash():
            path = self.file_path_var.get()
            if "No file" in path:
                messagebox.showerror("Error", "Please select a valid
