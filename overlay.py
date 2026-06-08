import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import csv
from PIL import Image, ImageTk
import cv2
import threading
import pygame
import textwrap
import re # <-- Modul baru untuk mencari Tag Emosi
import core
from core import chat_dengan_amadeus, fungsi_setup_database, hitung_saldo, ambil_riwayat_transaksi, hapus_transaksi, hapus_semua_transaksi, load_config, save_config, dapatkan_panggilan_user

class AmadeusVN:
    def __init__(self, root):
        self.root = root
        self.root.title("Amadeus System")
        self.root.geometry("1280x720")
        self.root.resizable(False, False)

        pygame.mixer.init()

        # Variabel Sistem
        self.playing_intro = True
        self.ui_aktif = False
        cfg = load_config()
        self.typing_speed = cfg.get("typing_speed", 30)
        self.is_typing = False
        self.type_timer = None
        self.sprites = {} # Dictionary penyimpan memori wajah
        self.pil_sprites = {} # Dictionary penyimpan PIL Image asli
        self.current_mood = "normal" # Menyimpan mood aktif saat ini
        self.overlay_panel = None
        self.active_tab = None

        # Memuat Video
        self.cap_intro = cv2.VideoCapture(r"dump req\intro.mp4")
        self.cap_bg = cv2.VideoCapture(r"dump req\background.mp4")

        # Canvas Utama
        self.canvas = tk.Canvas(self.root, width=1280, height=720, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.vid_img_on_canvas = self.canvas.create_image(0, 0, anchor=tk.NW)

        # Variabel Dialog
        self.text_chunks = []
        self.current_chunk = 0
        self.current_text_to_type = ""
        self.char_index = 0
        self.log_history = []

        # Tombol Skip Intro
        self.btn_skip = tk.Button(self.root, text="Skip Intro >>", font=("Consolas", 10, "bold"), bg="#111111", fg="white", relief=tk.FLAT, command=self.skip_intro)
        self.btn_skip.place(x=20, y=670, width=120, height=30)

        # Play Intro Audio
        try:
            pygame.mixer.music.load(r"dump req\intro.mp3")
            pygame.mixer.music.play()
        except:
            print("Peringatan: intro.mp3 tidak ditemukan.")

        self.root.bind("<space>", self.lanjutkan_dialog)
        self.update_video_frame()
        fungsi_setup_database()

    def skip_intro(self):
        if self.playing_intro:
            self.playing_intro = False
            try:
                self.cap_intro.release()
                pygame.mixer.music.stop()
            except:
                pass
            self.btn_skip.destroy()
            self.bangun_ui_utama()

    def bangun_ui_utama(self):
        if self.ui_aktif: return
        self.ui_aktif = True

        # 1. Memuat SEMUA Sprite Amadeus ke dalam Dictionary
        sprite_files = {
            "normal": r"dump req\amadeus_sprite\normal_amadeus.png",
            "mad": r"dump req\amadeus_sprite\mad_amadeus.png",
            "smiling": r"dump req\amadeus_sprite\smiling_amadeus.png",
            "thinking": r"dump req\amadeus_sprite\thinking_close_eye_amadeus.png",
            "look_away": r"dump req\amadeus_sprite\look_away_amadeus.png",
            "blushing_tsundere": r"dump req\amadeus_sprite\blushing_tsundere_amadeus.png" # Ekstra emosi!
        }

        for mood, filename in sprite_files.items():
            try:
                img_sprite = Image.open(filename)
                # Rasio 322x700 agar tidak gepeng
                img_sprite = img_sprite.resize((322, 700)) 
                self.pil_sprites[mood] = img_sprite
                self.sprites[mood] = ImageTk.PhotoImage(img_sprite)
            except Exception as e:
                print(f"Gagal memuat sprite {filename}: {e}")

        # Menampilkan sprite default (normal) dan menyimpan ID-nya agar bisa diganti-ganti
        self.sprite_on_canvas = self.canvas.create_image(640, 720, anchor=tk.S, image=self.sprites.get("normal", None))

        # 2. Kotak Dialog VN
        self.vn_frame = tk.Frame(self.root, bg="#111111", bd=2, relief=tk.RIDGE)
        self.vn_frame.place(x=240, y=560, width=800, height=140)

        self.vn_name = tk.Label(self.vn_frame, text="Amadeus", font=("Consolas", 14, "bold"), bg="#111111", fg="#00ffcc", anchor="w")
        self.vn_name.pack(fill=tk.X, padx=15, pady=(10, 0))

        panggilan = dapatkan_panggilan_user()
        if panggilan:
            teks_sambutan = f"Halo {panggilan}, aku Amadeus. Perlu bantuan laboratorium apa hari ini?"
        else:
            teks_sambutan = "Halo aku Amadeus, Asisten Laboratorium mu. Perlu apa hari ini?"

        self.vn_text = tk.Label(self.vn_frame, text=teks_sambutan, font=("Consolas", 12), bg="#111111", fg="white", justify=tk.LEFT, wraplength=770, anchor="nw")
        self.vn_text.pack(fill=tk.BOTH, expand=True, padx=15, pady=(5, 10))
        
        self.vn_text.bind("<Button-1>", self.lanjutkan_dialog)
        self.vn_frame.bind("<Button-1>", self.lanjutkan_dialog)

        # 3. Tombol Logo Vertikal
        self.icon_mic = None
        try:
            self.icon_out = ImageTk.PhotoImage(Image.open(r"dump req\logout_logo_red.png").resize((30, 30)))
            self.icon_log = ImageTk.PhotoImage(Image.open(r"dump req\logs_logo.png").resize((30, 30)))
            self.icon_set = ImageTk.PhotoImage(Image.open(r"dump req\settings_logo.png").resize((30, 30)))
            self.icon_mic = ImageTk.PhotoImage(Image.open(r"dump req\microphone.png").resize((25, 25)))

            tk.Button(self.root, image=self.icon_out, bg="#ffffff", bd=0, activebackground="#501010", command=self.root.quit).place(x=20, y=20, width=40, height=40)
            tk.Button(self.root, image=self.icon_log, bg="#ffffff", bd=0, activebackground="#333", command=lambda: self.tampilkan_menu_overlay("log")).place(x=20, y=70, width=40, height=40)
            tk.Button(self.root, image=self.icon_set, bg="#ffffff", bd=0, activebackground="#333", command=lambda: self.tampilkan_menu_overlay("settings")).place(x=20, y=120, width=40, height=40)
        except Exception as e:
            print(f"Gagal memuat ikon: {e}")

        # 4. Input Box & Mic Button
        self.placeholder_text = "(masukkan input disini)"
        self.entry_input = tk.Entry(self.root, bg="#2a2a2a", fg="gray", font=("Consolas", 11), insertbackground="white", relief=tk.FLAT)
        self.entry_input.place(x=960, y=20, width=255, height=35)
        
        if self.icon_mic:
            self.btn_mic = tk.Button(self.root, image=self.icon_mic, bg="#ffffff", 
                                     activebackground="#00ffcc", relief=tk.FLAT, bd=0,
                                     command=self.mulai_input_suara)
        else:
            self.btn_mic = tk.Button(self.root, text="🎙️", font=("Consolas", 12), bg="#ffffff", fg="black", 
                                     activebackground="#00ffcc", activeforeground="black", relief=tk.FLAT, bd=0,
                                     command=self.mulai_input_suara)
        self.btn_mic.place(x=1220, y=20, width=40, height=35)
        
        # Indikator Saldo UI (Clickable to open Transaction History)
        saldo_awal = hitung_saldo()
        self.label_saldo = tk.Label(self.root, text=f"Saldo: Rp {saldo_awal:,}", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="#00ffcc", anchor="e", cursor="hand2")
        self.label_saldo.place(x=960, y=60, width=300, height=25)
        self.label_saldo.bind("<Button-1>", lambda e: self.tampilkan_menu_overlay("transaksi"))
        self.label_saldo.bind("<Enter>", lambda e: self.label_saldo.config(bg="#2a2a2a"))
        self.label_saldo.bind("<Leave>", lambda e: self.label_saldo.config(bg="#1a1a1a"))

        # KODE BINDING YANG KEMBALI DITAMBAHKAN
        self.entry_input.insert(0, self.placeholder_text)
        self.entry_input.bind("<FocusIn>", self.hapus_placeholder)
        self.entry_input.bind("<FocusOut>", self.tambah_placeholder)
        self.entry_input.bind("<Return>", self.kirim_pesan)

    def hapus_placeholder(self, event):
        if self.entry_input.get() == self.placeholder_text:
            self.entry_input.delete(0, tk.END)
            self.entry_input.config(fg="white")

    def tambah_placeholder(self, event):
        if not self.entry_input.get():
            self.entry_input.insert(0, self.placeholder_text)
            self.entry_input.config(fg="gray")

    def update_video_frame(self):
        if self.playing_intro:
            ret, frame = self.cap_intro.read()
            if not ret:
                self.skip_intro()
                ret, frame = self.cap_bg.read()
        else:
            ret, frame = self.cap_bg.read()
            if not ret:
                self.cap_bg.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap_bg.read()

        if ret:
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame_pil = Image.fromarray(frame_rgb).resize((1280, 720))
            self.current_frame_tk = ImageTk.PhotoImage(frame_pil)
            self.canvas.itemconfig(self.vid_img_on_canvas, image=self.current_frame_tk)

        self.root.after(30, self.update_video_frame)

    # --- LOGIKA SEGMENTASI & EFEK KETIK ---
    def tampilkan_balasan(self, teks):
        teks = teks.strip()
        
        # Memecah teks menjadi halaman-halaman (chunks) yang pas di kotak dialog.
        # Kotak dialog muat sekitar 3-4 baris. Font Consolas 12 dengan wraplength 770
        # muat sekitar 90 karakter per baris. Jadi maksimum ~250 karakter per chunk.
        paragraphs = teks.split('\n\n')
        self.text_chunks = []
        
        current_chunk = []
        current_len = 0
        current_lines = 0
        
        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
                
            # Pecah paragraf menjadi baris-baris tunggal jika ada single newlines
            lines = para.split('\n')
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                
                # Estimasi jumlah baris yang dipakai oleh baris ini
                line_estimated_rows = max(1, (len(line) + 89) // 90)
                
                # Jika digabung melebihi batas 3 baris atau 250 karakter, buat chunk baru
                if current_lines + line_estimated_rows > 3 or current_len + len(line) > 250:
                    if current_chunk:
                        self.text_chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_len = len(line)
                    current_lines = line_estimated_rows
                else:
                    current_chunk.append(line)
                    current_len += len(line) + 1  # +1 untuk karakter newline
                    current_lines += line_estimated_rows
                    
            # Selesai satu paragraf, tutup chunk tersebut agar pembacaan nyaman
            if current_chunk:
                self.text_chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_len = 0
                current_lines = 0
                
        if current_chunk:
            self.text_chunks.append("\n".join(current_chunk))
            
        # Bersihkan chunk yang kosong
        self.text_chunks = [c.strip() for c in self.text_chunks if c.strip()]
        
        if not self.text_chunks:
            self.text_chunks = [teks]
                
        self.current_chunk = 0
        self.mulai_ketik_chunk()

    def mulai_ketik_chunk(self):
        if self.current_chunk < len(self.text_chunks):
            self.current_text_to_type = self.text_chunks[self.current_chunk]
            self.char_index = 0
            self.is_typing = True
            self.vn_text.config(text="")
            self.ketik_animasi()

    def ketik_animasi(self):
        if not self.is_typing: return 
        
        if self.char_index <= len(self.current_text_to_type):
            teks_sementara = self.current_text_to_type[:self.char_index]
            self.vn_text.config(text=teks_sementara)
            self.char_index += 1
            self.type_timer = self.root.after(self.typing_speed, self.ketik_animasi)
        else:
            self.is_typing = False
            if self.current_chunk < len(self.text_chunks) - 1:
                self.vn_text.config(text=self.current_text_to_type + " ▼")

    def lanjutkan_dialog(self, event=None):
        if event and event.keysym == 'space' and self.root.focus_get() == self.entry_input:
            return

        if self.is_typing:
            self.is_typing = False
            if self.type_timer:
                self.root.after_cancel(self.type_timer)
            teks_full = self.current_text_to_type
            if self.current_chunk < len(self.text_chunks) - 1:
                teks_full += " ▼"
            self.vn_text.config(text=teks_full)
        else:
            if self.text_chunks and self.current_chunk < len(self.text_chunks) - 1:
                self.current_chunk += 1
                self.mulai_ketik_chunk()

    # --- JENDELA TAMBAHAN (UNIFIED OVERLAY PANEL) ---
    def tampilkan_menu_overlay(self, tab_name):
        # 1. Jika panel sudah terbuka
        if self.overlay_panel:
            if self.active_tab == tab_name:
                # Klik tab yang sama -> tutup panel
                self.tutup_menu_overlay()
                return
            else:
                # Klik tab berbeda -> pindah tab
                self.active_tab = tab_name
                self.switch_tab(tab_name)
                return

        # 2. Jika panel belum terbuka -> Buat baru
        self.active_tab = tab_name
        
        # Frame Kontainer Overlay Utama
        self.overlay_panel = tk.Frame(self.root, bg="#161616", bd=2, relief=tk.RIDGE,
                                      highlightbackground="#00ffcc", highlightcolor="#00ffcc", highlightthickness=1)
        self.overlay_panel.place(x=240, y=60, width=800, height=480)

        # Header Bar / Navigation Tabs
        self.header_frame = tk.Frame(self.overlay_panel, bg="#111111", height=45)
        self.header_frame.pack(side=tk.TOP, fill=tk.X)
        self.header_frame.pack_propagate(False)

        # Tombol-tombol Tab
        self.tab_buttons = {}
        tabs = [
            ("transaksi", "💸 Transaksi"),
            ("log", "📜 System Log"),
            ("settings", "⚙️ Settings")
        ]
        
        for name, label in tabs:
            btn = tk.Button(self.header_frame, text=label, font=("Consolas", 10, "bold"),
                            bg="#111111", fg="gray", activebackground="#222222", activeforeground="#00ffcc",
                            relief=tk.FLAT, bd=0, padx=15,
                            command=lambda n=name: self.switch_tab(n))
            btn.pack(side=tk.LEFT, fill=tk.Y)
            
            # Hover effects
            btn.bind("<Enter>", lambda e, b=btn: self._on_tab_hover(b, True))
            btn.bind("<Leave>", lambda e, b=btn: self._on_tab_hover(b, False))
            
            self.tab_buttons[name] = btn

        # Tombol Close [X]
        btn_close = tk.Button(self.header_frame, text="✕ Close", font=("Consolas", 10, "bold"),
                              bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                              relief=tk.FLAT, bd=0, padx=15, command=self.tutup_menu_overlay)
        btn_close.pack(side=tk.RIGHT, fill=tk.Y)

        # Area Konten Utama
        self.content_frame = tk.Frame(self.overlay_panel, bg="#1a1a1a")
        self.content_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Pindah ke tab terpilih
        self.switch_tab(tab_name)

    def _on_tab_hover(self, button, is_enter):
        # Cari tahu apakah tombol ini sedang aktif
        current_tab = None
        for name, btn in self.tab_buttons.items():
            if btn == button:
                current_tab = name
                break
        
        if self.active_tab == current_tab:
            # Tetap pertahankan warna aktif
            button.config(bg="#222222", fg="#00ffcc")
        else:
            if is_enter:
                button.config(bg="#222222", fg="white")
            else:
                button.config(bg="#111111", fg="gray")

    def tutup_menu_overlay(self):
        if self.overlay_panel:
            self.overlay_panel.destroy()
            self.overlay_panel = None
            self.active_tab = None

    def switch_tab(self, tab_name):
        self.active_tab = tab_name
        
        # Update styling tombol tab
        for name, btn in self.tab_buttons.items():
            if name == tab_name:
                btn.config(bg="#222222", fg="#00ffcc")
            else:
                btn.config(bg="#111111", fg="gray")

        # Hancurkan konten tab sebelumnya jika ada
        for widget in self.content_frame.winfo_children():
            widget.destroy()

        # Render tab yang baru
        if tab_name == "transaksi":
            self.render_tab_transaksi()
        elif tab_name == "log":
            self.render_tab_log()
        elif tab_name == "settings":
            self.render_tab_settings()

    def render_tab_transaksi(self):
        # Configure styles untuk Treeview agar bernuansa dark/cyberpunk
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Custom.Treeview", 
                        background="#1a1a1a", 
                        foreground="white", 
                        fieldbackground="#1a1a1a", 
                        rowheight=25,
                        font=("Consolas", 10))
        style.map("Custom.Treeview", 
                  background=[("selected", "#333333")], 
                  foreground=[("selected", "#00ffcc")])
        style.configure("Custom.Treeview.Heading", 
                        background="#2a2a2a", 
                        foreground="white", 
                        font=("Consolas", 10, "bold"),
                        borderwidth=0)

        # Judul Tab
        lbl_title = tk.Label(self.content_frame, text="Riwayat Transaksi Finansial Amadeus", 
                             font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
        lbl_title.pack(anchor="w", padx=15, pady=(15, 5))

        # Container Frame untuk Treeview dan Scrollbar
        tree_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        tree_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # Setup columns
        cols = ("ID", "Waktu", "Jenis", "Nominal", "Kategori", "Deskripsi")
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Custom.Treeview")
        
        # Scrollbar
        scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Set Column Headings & Widths
        self.tree.heading("ID", text="ID")
        self.tree.heading("Waktu", text="Waktu / Tanggal")
        self.tree.heading("Jenis", text="Jenis")
        self.tree.heading("Nominal", text="Nominal")
        self.tree.heading("Kategori", text="Kategori")
        self.tree.heading("Deskripsi", text="Deskripsi")

        self.tree.column("ID", width=40, minwidth=30, anchor=tk.CENTER)
        self.tree.column("Waktu", width=140, minwidth=120, anchor=tk.CENTER)
        self.tree.column("Jenis", width=90, minwidth=80, anchor=tk.CENTER)
        self.tree.column("Nominal", width=110, minwidth=90, anchor=tk.E)
        self.tree.column("Kategori", width=110, minwidth=90, anchor=tk.W)
        self.tree.column("Deskripsi", width=220, minwidth=150, anchor=tk.W)

        # Tags untuk mewarnai baris pemasukan/pengeluaran
        self.tree.tag_configure("pemasukan", foreground="#00ff88")
        self.tree.tag_configure("pengeluaran", foreground="#ff4444")

        # Fungsi memuat data ke Treeview
        def isi_tabel():
            for item in self.tree.get_children():
                self.tree.delete(item)
            
            records = ambil_riwayat_transaksi()
            for r_id, tgl, jns, nom, kat, dsk in records:
                tag = "pemasukan" if jns.lower() == "pemasukan" else "pengeluaran"
                nominal_fmt = f"Rp {nom:,}"
                self.tree.insert("", tk.END, values=(r_id, tgl, jns.upper(), nominal_fmt, kat, dsk), tags=(tag,))
        
        isi_tabel()

        # Bottom Bar untuk Aksi
        control_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=15)

        # Info Label
        lbl_info = tk.Label(control_frame, text="*Gunakan tombol di kanan untuk mengelola atau menganalisis data.", 
                            font=("Consolas", 8, "italic"), bg="#1a1a1a", fg="gray")
        lbl_info.pack(side=tk.LEFT)

        # Tombol Analisis AI
        btn_analisis = tk.Button(control_frame, text="📊 Analisis AI", font=("Consolas", 9, "bold"),
                                 bg="#115e59", fg="white", activebackground="#14b8a6", activeforeground="white",
                                 relief=tk.FLAT, command=self.minta_analisis_pengeluaran, padx=10, pady=5)
        btn_analisis.pack(side=tk.RIGHT, padx=5)

        # Tombol Export CSV
        btn_export = tk.Button(control_frame, text="Export CSV", font=("Consolas", 9, "bold"),
                               bg="#1e293b", fg="white", activebackground="#334155", activeforeground="white",
                               relief=tk.FLAT, command=self.ekspor_riwayat_csv, padx=10, pady=5)
        btn_export.pack(side=tk.RIGHT, padx=5)

        # Tombol Hapus Semua
        btn_hapus_semua = tk.Button(control_frame, text="Hapus Semua", font=("Consolas", 9, "bold"),
                                    bg="#7f1d1d", fg="white", activebackground="#b91c1c", activeforeground="white",
                                    relief=tk.FLAT, command=self.hapus_seluruh_riwayat, padx=10, pady=5)
        btn_hapus_semua.pack(side=tk.RIGHT, padx=5)

        # Tombol Hapus Terpilih
        def proses_hapus():
            selected = self.tree.selection()
            if not selected:
                return
            
            item_values = self.tree.item(selected[0], "values")
            t_id = item_values[0]
            
            if hapus_transaksi(t_id):
                print(f"[SYSTEM LOG] Transaksi ID {t_id} berhasil dihapus.")
                self.log_history.append(f"[SYSTEM]\nTransaksi ID {t_id} dihapus. Saldo diperbarui.")
                isi_tabel()
                
                # Update saldo HUD di main UI
                saldo_baru = hitung_saldo()
                self.label_saldo.config(text=f"Saldo: Rp {saldo_baru:,}")
                
        btn_hapus = tk.Button(control_frame, text="Hapus Terpilih", font=("Consolas", 9, "bold"),
                              bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                              relief=tk.FLAT, command=proses_hapus, padx=10, pady=5)
        btn_hapus.pack(side=tk.RIGHT, padx=5)

    def render_tab_log(self):
        # Judul Tab
        lbl_title = tk.Label(self.content_frame, text="System & Conversation Logs", 
                             font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
        lbl_title.pack(anchor="w", padx=15, pady=(15, 5))

        # Area ScrolledText
        log_area = scrolledtext.ScrolledText(self.content_frame, bg="#111111", fg="#e0e0e0", 
                                             font=("Consolas", 10), wrap=tk.WORD, bd=0, highlightthickness=0)
        log_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        # Masukkan log history
        for baris in self.log_history:
            log_area.insert(tk.END, baris + "\n\n")
        log_area.config(state=tk.DISABLED)
        log_area.see(tk.END)

        # Control Frame
        control_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=15)

        # Tombol Bersihkan Log
        def bersihkan_log():
            self.log_history.clear()
            log_area.config(state=tk.NORMAL)
            log_area.delete("1.0", tk.END)
            log_area.config(state=tk.DISABLED)
            print("[SYSTEM LOG] Log obrolan dibersihkan.")

        btn_clear = tk.Button(control_frame, text="Clear Log History", font=("Consolas", 9, "bold"),
                              bg="#333333", fg="white", activebackground="#555555", activeforeground="white",
                              relief=tk.FLAT, command=bersihkan_log, padx=10, pady=5)
        btn_clear.pack(side=tk.RIGHT)

    def render_tab_settings(self):
        # Judul Tab
        lbl_title = tk.Label(self.content_frame, text="Amadeus Settings & Configuration", 
                             font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
        lbl_title.pack(anchor="w", padx=15, pady=(10, 10))

        # --- SEKTOR 1: KECEPATAN TEKS ---
        lbl_speed = tk.Label(self.content_frame, text="Text Typing Speed (ms/character):", 
                             font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
        lbl_speed.pack(anchor="w", padx=20)
        
        speed_slider = tk.Scale(self.content_frame, from_=10, to=150, orient=tk.HORIZONTAL, 
                                bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                                activebackground="#00ffcc")
        speed_slider.set(self.typing_speed)
        speed_slider.pack(anchor="w", padx=20, pady=(0, 10))

        # --- SEKTOR 2: PEMILIHAN OTAK AI ---
        lbl_brain = tk.Label(self.content_frame, text="AI Brain Source (Mode AI):", 
                             font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
        lbl_brain.pack(anchor="w", padx=20)
        
        core_mode = core.MODE_AI_AKTIF
        if core_mode == "cloud":
            core_mode = "cloud_2_5"
        self.var_ai_mode = tk.StringVar(value=core_mode)
        
        frame_radio = tk.Frame(self.content_frame, bg="#1a1a1a")
        frame_radio.pack(anchor="w", padx=20, pady=5)

        r_local = tk.Radiobutton(frame_radio, text="Lokal (Ollama)", variable=self.var_ai_mode, value="local", 
                                bg="#1a1a1a", fg="#00ffcc", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                activeforeground="#00ffcc", font=("Consolas", 10))
        r_local.pack(side=tk.LEFT, padx=(0, 15))
        
        r_cloud_2_5 = tk.Radiobutton(frame_radio, text="Gemini 2.5", variable=self.var_ai_mode, value="cloud_2_5", 
                                    bg="#1a1a1a", fg="#ffcc00", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                    activeforeground="#ffcc00", font=("Consolas", 10))
        r_cloud_2_5.pack(side=tk.LEFT, padx=(0, 15))

        r_cloud_3_5 = tk.Radiobutton(frame_radio, text="Gemini 3.5", variable=self.var_ai_mode, value="cloud_3_5", 
                                    bg="#1a1a1a", fg="#e11d48", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                    activeforeground="#e11d48", font=("Consolas", 10))
        r_cloud_3_5.pack(side=tk.LEFT)

        lbl_warning = tk.Label(self.content_frame, text="*Mengubah mode otak akan mereset ingatan sesi aktif Amadeus.", 
                               font=("Consolas", 8, "italic"), bg="#1a1a1a", fg="gray")
        lbl_warning.pack(anchor="w", padx=20, pady=(0, 5))

        # --- SEKTOR 3: MEMORI USER (TENTANG SAYA) ---
        lbl_memory = tk.Label(self.content_frame, text="User Memory (Informasi Tentang Saya):", 
                              font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
        lbl_memory.pack(anchor="w", padx=20, pady=(5, 2))
        
        cfg = load_config()
        user_mem = cfg.get("user_memory", "")
        
        self.txt_memory = tk.Text(self.content_frame, bg="#111111", fg="white", 
                                  font=("Consolas", 9), insertbackground="white", 
                                  height=3, width=70, relief=tk.FLAT)
        self.txt_memory.pack(anchor="w", padx=20, pady=(0, 5))
        self.txt_memory.insert(tk.END, user_mem)

        # Label status keberhasilan
        lbl_status = tk.Label(self.content_frame, text="", font=("Consolas", 10, "bold"), bg="#1a1a1a")
        lbl_status.pack(anchor="w", padx=20, pady=2)

        # --- TOMBOL SIMPAN ---
        def simpan_setting_hybrid():
            # 1. Ambil teks memori dari Text widget
            user_mem_value = self.txt_memory.get("1.0", tk.END).strip()
            
            # 2. Simpan kecepatan teks
            self.typing_speed = speed_slider.get()
            
            # 3. Simpan mode AI
            mode_terpilih = self.var_ai_mode.get()
            
            # 4. Tulis ke file amadeus_config.json
            cfg_data = {
                "typing_speed": self.typing_speed,
                "ai_mode": mode_terpilih,
                "user_memory": user_mem_value
            }
            save_config(cfg_data)
            
            # Terapkan mode AI ke core.py
            from core import set_mode_ai
            set_mode_ai(mode_terpilih)
            
            # Tampilkan indikator visual singkat
            if mode_terpilih == "local":
                mode_text = "LOKAL"
            elif mode_terpilih == "cloud_2_5":
                mode_text = "GEMINI 2.5"
            else:
                mode_text = "GEMINI 3.5"
                
            self.label_saldo.config(text=f"Mode AI: {mode_text}")
            self.root.after(2000, lambda: self.label_saldo.config(text=f"Saldo: Rp {hitung_saldo():,}"))
            
            # Log
            self.log_history.append(f"[SYSTEM]\nPengaturan disimpan. Text Speed: {self.typing_speed}ms. Mode AI: {mode_text}. Memory updated.")
            
            # Feedback visual di dalam tab
            lbl_status.config(text="✓ Pengaturan & Memori berhasil disimpan!", fg="#00ff88")
            self.root.after(2000, lambda: lbl_status.config(text="") if lbl_status.winfo_exists() else None)

        btn_save = tk.Button(self.content_frame, text="Save & Apply Settings", font=("Consolas", 10, "bold"), 
                             bg="#222222", fg="white", activebackground="#333333", activeforeground="#00ffcc",
                             relief=tk.FLAT, command=simpan_setting_hybrid, padx=15, pady=8)
        btn_save.pack(anchor="w", padx=20, pady=10)

# --- LOGIKA KOMUNIKASI & EKSPRESI ---
    def ekstrak_emosi_dan_bersihkan_teks(self, balasan):
        mood_terdeteksi = "normal"
        # Cari tag dalam kurung siku di awal/awal teks, misalnya [normal] atau [smerah]
        match = re.search(r'\[([a-zA-Z0-9_\s\-]+)\]', balasan)
        if match:
            tag_raw = match.group(1).lower().strip()
            # Pemetaan tag emosi alternatif ke sprite yang ada
            pemetaan_emosi = {
                "normal": "normal",
                "mad": "mad",
                "marah": "mad",
                "smiling": "smiling",
                "senyum": "smiling",
                "thinking": "thinking",
                "mikir": "thinking",
                "look_away": "look_away",
                "ragu": "look_away",
                "blushing_tsundere": "blushing_tsundere",
                "blushing": "blushing_tsundere",
                "tsundere": "blushing_tsundere",
                "smerah": "blushing_tsundere",
                "malu": "blushing_tsundere"
            }
            mood_terdeteksi = pemetaan_emosi.get(tag_raw, "normal")
            # Hapus tag kurung siku pertama
            balasan = re.sub(r'\[.*?\]', '', balasan, count=1).strip()
            
        return mood_terdeteksi, balasan

    def play_voice_sfx(self, mood):
        import os
        voice_files = {
            "normal": r"dump req\voice_normal.wav",
            "mad": r"dump req\voice_mad.wav",
            "smiling": r"dump req\voice_smiling.wav",
            "thinking": r"dump req\voice_thinking.wav",
            "look_away": r"dump req\voice_look_away.wav",
            "blushing_tsundere": r"dump req\voice_blushing_tsundere.wav"
        }
        
        if mood in voice_files:
            file_path = voice_files[mood]
            if os.path.exists(file_path):
                try:
                    voice_sound = pygame.mixer.Sound(file_path)
                    voice_sound.set_volume(0.6) # Volume suara Kurisu sedikit lebih keras
                    voice_sound.play()
                except Exception as e:
                    print(f"[SYSTEM LOG] Gagal memutar suara Kurisu ({mood}): {e}")

    def generate_glitch_frame(self, original_image):
        import random
        from PIL import ImageDraw
        width, height = original_image.size
        glitch_img = original_image.convert("RGBA")
        draw = ImageDraw.Draw(glitch_img)
        
        # 1. Shift random horizontal strips
        for _ in range(random.randint(4, 9)):
            strip_h = random.randint(8, 30)
            y_pos = random.randint(0, height - strip_h)
            x_shift = random.randint(-40, 40)
            
            strip = original_image.crop((0, y_pos, width, y_pos + strip_h))
            glitch_img.paste(strip, (x_shift, y_pos))
            
        # 2. Gambar balok warna semi-transparan (Merah/Cyan/Magenta/Kuning)
        for _ in range(random.randint(2, 5)):
            y_pos = random.randint(0, height - 20)
            bar_h = random.randint(4, 12)
            color = random.choice([
                (230, 15, 15, 150),   # Merah
                (15, 230, 230, 150),  # Cyan
                (230, 15, 230, 150),  # Magenta
                (230, 230, 15, 150)   # Kuning
            ])
            draw.rectangle([0, y_pos, width, y_pos + bar_h], fill=color)
            
        return glitch_img

    def trigger_glitch_transition(self, target_mood):
        if target_mood not in self.pil_sprites:
            return
            
        if target_mood != self.current_mood:
            self.current_mood = target_mood
            self.play_voice_sfx(target_mood)
            
            pil_base = self.pil_sprites[target_mood]
            glitch_frame_1 = self.generate_glitch_frame(pil_base)
            glitch_frame_2 = self.generate_glitch_frame(pil_base)
            
            self.glitch_tk1 = ImageTk.PhotoImage(glitch_frame_1)
            self.glitch_tk2 = ImageTk.PhotoImage(glitch_frame_2)
            
            self.canvas.itemconfig(self.sprite_on_canvas, image=self.glitch_tk1)
            
            def step2():
                self.canvas.itemconfig(self.sprite_on_canvas, image=self.glitch_tk2)
                def step_final():
                    self.canvas.itemconfig(self.sprite_on_canvas, image=self.sprites[target_mood])
                    self.glitch_tk1 = None
                    self.glitch_tk2 = None
                self.root.after(70, step_final)
                
            self.root.after(70, step2)
        else:
            self.canvas.itemconfig(self.sprite_on_canvas, image=self.sprites[target_mood])

    def proses_pesan_ai(self, pesan_user):
        mode_aktif = core.MODE_AI_AKTIF
        if mode_aktif == "local":
            target_brain = "Ollama Lokal"
            loading_text = "Memproses analisis data Llama lokal..."
        elif mode_aktif == "cloud_2_5":
            target_brain = "Gemini 2.5 Cloud"
            loading_text = "Memproses analisis data Gemini 2.5 cloud..."
        else:
            target_brain = "Gemini 3.5 Cloud"
            loading_text = "Memproses analisis data Gemini 3.5 cloud..."

        # 1. Update UI: Tampilkan status loading secara aman
        self.root.after(0, lambda: self.vn_text.config(text=loading_text))
        print(f"[SYSTEM LOG] Mengirim permintaan ke {target_brain}: '{pesan_user}'")
        
        # Inisialisasi variabel default
        balasan = ""
        mood_terdeteksi = "normal"

        try:
            # 2. Panggil fungsi berat (blocking call)
            balasan = chat_dengan_amadeus(pesan_user)
            
            # Jika balasan kosong
            if not balasan or not balasan.strip():
                raise Exception(f"{target_brain} tidak memberikan respons.")

            print(f"[SYSTEM LOG] Respons diterima dari {target_brain}.")

            # 3. Analisis Emosi
            mood_terdeteksi, balasan = self.ekstrak_emosi_dan_bersihkan_teks(balasan)
            
            # 4. Fungsi Eksekusi UI Sukses (lempar ke main thread)
            def update_ui_sukses():
                if mood_terdeteksi in self.sprites:
                    self.trigger_glitch_transition(mood_terdeteksi)
                
                # Refresh angka saldo di layar
                saldo_baru = hitung_saldo()
                self.label_saldo.config(text=f"Saldo: Rp {saldo_baru:,}")
                
                self.log_history.append(f"[Amadeus]\n{balasan}")
                self.tampilkan_balasan(balasan)
            
            self.root.after(0, update_ui_sukses)

        except Exception as e:
            # 5. JIKA ERROR TERJADI
            if mode_aktif.startswith("cloud"):
                error_msg = f"Koneksi ke otak cloud terputus. Pastikan API key valid atau kuota tidak habis.\nLog: {str(e)}"
            else:
                error_msg = f"Koneksi ke otak lokal terputus. Pastikan Ollama menyala di latar belakang.\nLog: {str(e)}"
            print(f"[ERROR] {error_msg}")
            
            # Paksa UI menampilkan error, jangan stuck di "Memproses..."
            def update_ui_error():
                # Ganti wajah ke normal atau thinking (wajah panik/bingung)
                if "thinking" in self.sprites:
                    self.canvas.itemconfig(self.sprite_on_canvas, image=self.sprites["thinking"])
                
                self.vn_text.config(text=error_msg)
                # Tandai ketik selesai agar spasi bisa jalan lagi
                self.is_typing = False 

            self.root.after(0, update_ui_error)

    def kirim_pesan(self, event):
        pesan = self.entry_input.get()
        if not pesan.strip() or pesan == self.placeholder_text: return
        
        self.entry_input.delete(0, tk.END)
        self.entry_input.config(fg="white")
        self.log_history.append(f"[Kamu]\n{pesan}")
        threading.Thread(target=self.proses_pesan_ai, args=(pesan,), daemon=True).start()

    def mulai_input_suara(self):
        # 1. Cek apakah library sudah terinstall
        try:
            import speech_recognition as sr
            import pyaudio
        except ImportError:
            messagebox.showerror(
                "Library Pendukung Kurang", 
                "Untuk menggunakan input suara, silakan jalankan perintah berikut di terminal Anda:\n\n"
                "pip install SpeechRecognition pyaudio"
            )
            return

        # 2. Amankan UI saat merekam
        self.entry_input.config(state=tk.DISABLED)
        self.btn_mic.config(state=tk.DISABLED, bg="#501010")
        
        # Tampilkan visual status mendengarkan
        self.vn_text.config(text="Amadeus sedang mendengarkan suara Anda... 🎙️")
        
        # Jalankan di background thread agar UI tkinter tidak beku
        threading.Thread(target=self._proses_input_suara_thread, daemon=True).start()

    def _proses_input_suara_thread(self):
        import speech_recognition as sr
        r = sr.Recognizer()
        
        recognized_text = ""
        error_occurred = False
        error_msg = ""
        
        try:
            with sr.Microphone() as source:
                # Menyesuaikan dengan kebisingan sekitar selama 0.5 detik
                r.adjust_for_ambient_noise(source, duration=0.5)
                # Mendengarkan input audio
                audio = r.listen(source, timeout=4, phrase_time_limit=8)
                
            # Menggunakan API Google Web Speech dengan opsi Bahasa Indonesia
            recognized_text = r.recognize_google(audio, language="id-ID")
            print(f"[SYSTEM LOG] Hasil Perekaman Suara: '{recognized_text}'")
            
        except sr.WaitTimeoutError:
            error_occurred = True
            error_msg = "Waktu habis, suara tidak terdeteksi."
        except sr.UnknownValueError:
            error_occurred = True
            error_msg = "Suara tidak terdengar jelas atau tidak dipahami."
        except sr.RequestError as e:
            error_occurred = True
            error_msg = f"Gagal menghubungi Google Speech API; {e}"
        except Exception as e:
            error_occurred = True
            error_msg = f"Terjadi kesalahan perekaman: {e}"

        # Kembalikan kondisi UI di main thread
        def update_ui_akhir():
            self.entry_input.config(state=tk.NORMAL)
            self.btn_mic.config(state=tk.NORMAL, bg="#ffffff")
            
            if error_occurred:
                self.vn_text.config(text=f"[Gagal mendengarkan] {error_msg}")
                self.log_history.append(f"[SYSTEM]\nPerekaman suara gagal: {error_msg}")
            else:
                # Masukkan hasil transkripsi ke input box
                self.entry_input.delete(0, tk.END)
                self.entry_input.insert(0, recognized_text)
                self.entry_input.config(fg="white")
                
                # Kirim langsung pesan tersebut
                self.kirim_pesan(None)

        self.root.after(0, update_ui_akhir)

    def ekspor_riwayat_csv(self):
        records = ambil_riwayat_transaksi()
        if not records:
            messagebox.showinfo("Informasi", "Tidak ada transaksi untuk diekspor.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Simpan Riwayat Transaksi"
        )
        if not file_path:
            return
            
        try:
            with open(file_path, mode='w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                # Header
                writer.writerow(["ID", "Tanggal", "Jenis", "Nominal", "Kategori", "Deskripsi"])
                # Data
                writer.writerows(records)
            
            messagebox.showinfo("Sukses", f"Riwayat transaksi berhasil diekspor ke:\n{file_path}")
            self.log_history.append(f"[SYSTEM]\nRiwayat transaksi diekspor ke {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mengekspor data:\n{e}")

    def hapus_seluruh_riwayat(self):
        confirm = messagebox.askyesno(
            "Konfirmasi", 
            "Apakah Anda yakin ingin menghapus seluruh riwayat transaksi? Tindakan ini tidak bisa dibatalkan."
        )
        if not confirm:
            return
            
        if hapus_semua_transaksi():
            messagebox.showinfo("Sukses", "Semua riwayat transaksi berhasil dihapus.")
            self.log_history.append("[SYSTEM]\nSemua riwayat transaksi dibersihkan.")
            
            # Update saldo HUD di main UI
            self.label_saldo.config(text=f"Saldo: Rp 0")
            
            # Jika overlay panel sedang terbuka di tab transaksi, refresh
            if self.active_tab == "transaksi":
                self.render_tab_transaksi()
        else:
            messagebox.showerror("Error", "Gagal menghapus seluruh riwayat transaksi.")

    def minta_analisis_pengeluaran(self):
        records = ambil_riwayat_transaksi()
        if not records:
            messagebox.showinfo("Informasi", "Belum ada data transaksi yang bisa dianalisis oleh Amadeus.")
            return

        total_pemasukan = 0
        total_pengeluaran = 0
        kategori_pengeluaran = {}
        
        detail_transaksi = []
        for _, tgl, jenis, nominal, kategori, deskripsi in records:
            if jenis.lower() == "pemasukan":
                total_pemasukan += nominal
            else:
                total_pengeluaran += nominal
                kategori_pengeluaran[kategori] = kategori_pengeluaran.get(kategori, 0) + nominal
            
            detail_transaksi.append(f"- {tgl[:10]} | {jenis.upper()} | Rp {nominal:,} | {kategori} ({deskripsi})")
            
        summary_lines = [
            f"Total Pemasukan: Rp {total_pemasukan:,}",
            f"Total Pengeluaran: Rp {total_pengeluaran:,}",
            "Pengeluaran Per Kategori:"
        ]
        for kat, nom in kategori_pengeluaran.items():
            summary_lines.append(f"  * {kat}: Rp {nom:,}")
            
        summary_lines.append("\nDaftar Transaksi Terbaru:")
        summary_lines.extend(detail_transaksi[:15]) # ambil 15 transaksi terakhir untuk menghemat token
        
        summary_text = "\n".join(summary_lines)
        
        # Tutup panel menu overlay agar user bisa melihat interaksi karakter
        self.tutup_menu_overlay()
        
        # Mulai thread untuk memproses analisis data keuangan
        threading.Thread(target=self._proses_analisis_pengeluaran_thread, args=(summary_text,), daemon=True).start()

    def _proses_analisis_pengeluaran_thread(self, summary_text):
        mode_aktif = core.MODE_AI_AKTIF
        if mode_aktif == "local":
            target_brain = "Ollama Lokal"
            loading_text = "Menganalisis data keuangan di Llama lokal..."
        elif mode_aktif == "cloud_2_5":
            target_brain = "Gemini 2.5 Cloud"
            loading_text = "Menganalisis data keuangan di Gemini 2.5 cloud..."
        else:
            target_brain = "Gemini 3.5 Cloud"
            loading_text = "Menganalisis data keuangan di Gemini 3.5 cloud..."

        self.root.after(0, lambda: self.vn_text.config(text=loading_text))
        print(f"[SYSTEM LOG] Meminta {target_brain} untuk menganalisis pengeluaran.")

        prompt = f"""[MINTA ANALISIS FINANSIAL]
Analisis data transaksi keuangan saya berikut ini. Berikan kritik, saran hemat, atau pujian jika pengelolaan uang saya sudah baik dengan gaya bicara khas Makise Kurisu / Amadeus (casual Indonesian, tsundere, smart, agak sarkastik tapi peduli).
Catatan: JANGAN mengeluarkan output JSON transaksi finansial untuk obrolan ini, cukup berikan respon teks analisis saja.

Data Ringkasan Transaksi:
{summary_text}
"""
        
        balasan = ""
        mood_terdeteksi = "normal"

        try:
            balasan = chat_dengan_amadeus(prompt)
            
            if not balasan or not balasan.strip():
                raise Exception(f"{target_brain} tidak memberikan respons.")

            print(f"[SYSTEM LOG] Analisis finansial diterima dari {target_brain}.")

            # Analisis Emosi
            had_tag = bool(re.search(r'\[([a-zA-Z0-9_\s\-]+)\]', balasan))
            mood_terdeteksi, balasan = self.ekstrak_emosi_dan_bersihkan_teks(balasan)
            if not had_tag:
                mood_terdeteksi = "thinking"
            
            # UI update sukses
            def update_ui_sukses():
                if mood_terdeteksi in self.sprites:
                    self.trigger_glitch_transition(mood_terdeteksi)
                self.log_history.append(f"[Amadeus (Analisis Finansial)]\n{balasan}")
                self.tampilkan_balasan(balasan)
            
            self.root.after(0, update_ui_sukses)

        except Exception as e:
            error_msg = f"Koneksi ke {target_brain} terputus saat menganalisis data.\nLog: {str(e)}"
            print(f"[ERROR] {error_msg}")
            
            def update_ui_error():
                if "thinking" in self.sprites:
                    self.canvas.itemconfig(self.sprite_on_canvas, image=self.sprites["thinking"])
                self.vn_text.config(text=error_msg)
                self.is_typing = False

            self.root.after(0, update_ui_error)

if __name__ == "__main__":
    root = tk.Tk()
    app = AmadeusVN(root)
    root.mainloop()