import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import csv
from PIL import Image, ImageTk
import cv2
import threading
import pygame
import textwrap
import re # <-- Modul baru untuk mencari Tag Emosi
import queue # <-- Tambahkan Queue untuk Video Threading
import core
from core import chat_dengan_amadeus, fungsi_setup_database, hitung_saldo, ambil_riwayat_transaksi, hapus_transaksi, hapus_semua_transaksi, load_config, save_config, dapatkan_panggilan_user

class AmadeusVN:
    def __init__(self, root):
        self.root = root
        self.root.title("Amadeus System")
        self.root.geometry("1280x720")
        self.root.resizable(False, False)

        pygame.mixer.init()

        # Set Windows App Logo Icon
        try:
            app_logo = Image.open(r"dump req\AmadeusLogo.png")
            self.app_logo_img = ImageTk.PhotoImage(app_logo)
            self.root.iconphoto(False, self.app_logo_img)
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal menyetel logo aplikasi: {e}")

        # Audio & video queues initialization
        self.sound_cache = {}
        self.video_queue = queue.Queue(maxsize=5)
        self.video_thread_running = True
        self.update_video_active = True
        self.intro_finished = False

        # Variabel Sistem
        self.playing_intro = True
        self.ui_aktif = False
        cfg = load_config()
        self.typing_speed = cfg.get("typing_speed", 30)
        self.voice_volume = cfg.get("voice_volume", 70) / 100.0
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

        # Start Video Thread
        self.video_thread = threading.Thread(target=self.run_video_thread, daemon=True)
        self.video_thread.start()

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
            pygame.mixer.music.set_volume(self.voice_volume)
            pygame.mixer.music.play()
        except:
            print("Peringatan: intro.mp3 tidak ditemukan.")

        self.root.bind("<space>", self.lanjutkan_dialog)
        self.update_video_active = True
        self.update_video_frame()
        fungsi_setup_database()
        self.start_telegram_bot_thread()

        # Setup System Tray
        self.setup_system_tray()

        # Safe closing handler (Hanya menyembunyikan ke System Tray)
        self.root.protocol("WM_DELETE_WINDOW", self.sembunyikan_ke_tray)

    def skip_intro(self):
        if self.playing_intro:
            self.playing_intro = False
            try:
                self.cap_intro.release()
                pygame.mixer.music.stop()
            except:
                pass
            # Bersihkan antrean agar frame intro lama tidak dimunculkan lagi
            while not self.video_queue.empty():
                try:
                    self.video_queue.get_nowait()
                except:
                    break
            self.btn_skip.destroy()
            self.bangun_ui_utama()

    def get_sprite(self, mood):
        if mood in self.sprites:
            return self.sprites[mood]
            
        sprite_files = {
            "normal": r"dump req\amadeus_sprite\normal_amadeus.png",
            "mad": r"dump req\amadeus_sprite\mad_amadeus.png",
            "smiling": r"dump req\amadeus_sprite\smiling_amadeus.png",
            "thinking": r"dump req\amadeus_sprite\thinking_close_eye_amadeus.png",
            "look_away": r"dump req\amadeus_sprite\look_away_amadeus.png",
            "blushing_tsundere": r"dump req\amadeus_sprite\blushing_tsundere_amadeus.png"
        }
        
        filename = sprite_files.get(mood)
        if not filename:
            print(f"[SYSTEM LOG] Mood '{mood}' tidak dikenal, fallback ke 'normal'.")
            return self.get_sprite("normal")
            
        try:
            print(f"[SYSTEM LOG] Lazy-loading sprite mood: {mood} dari {filename}")
            img_sprite = Image.open(filename)
            img_sprite = img_sprite.resize((322, 700))
            self.pil_sprites[mood] = img_sprite
            self.sprites[mood] = ImageTk.PhotoImage(img_sprite)
            return self.sprites[mood]
        except Exception as e:
            print(f"Gagal memuat sprite {filename}: {e}")
            if mood != "normal":
                return self.get_sprite("normal")
            return None

    def bangun_ui_utama(self):
        if self.ui_aktif: return
        self.ui_aktif = True

        # 1. Memuat sprite default (normal) secara lazy loading
        self.get_sprite("normal")

        # Menampilkan sprite default (normal) dan menyimpan ID-nya agar bisa diganti-ganti
        self.sprite_on_canvas = self.canvas.create_image(640, 720, anchor=tk.S, image=self.sprites.get("normal", None))

        # 2. Kotak Dialog VN
        self.vn_frame = tk.Frame(self.root, bg="#111111", bd=2, relief=tk.RIDGE)
        self.vn_frame.place(x=240, y=560, width=800, height=140)

        self.vn_name = tk.Label(self.vn_frame, text="Amadeus", font=("Consolas", 14, "bold"), bg="#111111", fg="#00ffcc", anchor="w")
        self.vn_name.pack(fill=tk.X, padx=15, pady=(10, 0))

        panggilan = dapatkan_panggilan_user()
        import random
        # Pool greeting: (file_audio, teks_tampilan)
        greeting_pool = [
            (
                "CRS_0000n.wav", 
                f"Selamat pagi, kamu. " + (f"Halo {panggilan}, aku Amadeus. Perlu bantuan laboratorium apa hari ini?" if panggilan else "Halo aku Amadeus, Asisten Laboratorium mu. Perlu apa hari ini?")
            ),
            (
                "CRS_0130.wav", 
                f"Ngomong-ngomong, aku belum memperkenalkan diri secara resmi ya. Aku Makise Kurisu. Salam kenal. " + (f"Halo {panggilan}, mari kita mulai hari ini." if panggilan else "Halo, mari kita mulai hari ini.")
            )
        ]
        
        selected_audio, teks_sambutan = random.choice(greeting_pool)
        self.play_specific_voice(selected_audio)

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
            self.icon_chart = ImageTk.PhotoImage(Image.open(r"dump req\bar-chart.png").resize((30, 30)))

            tk.Button(self.root, image=self.icon_out, bg="#ffffff", bd=0, activebackground="#501010", command=self.keluar_aplikasi).place(x=20, y=20, width=40, height=40)
            tk.Button(self.root, image=self.icon_log, bg="#ffffff", bd=0, activebackground="#333", command=lambda: self.tampilkan_menu_overlay("log")).place(x=20, y=70, width=40, height=40)
            tk.Button(self.root, image=self.icon_set, bg="#ffffff", bd=0, activebackground="#333", command=lambda: self.tampilkan_menu_overlay("settings")).place(x=20, y=120, width=40, height=40)
            tk.Button(self.root, image=self.icon_chart, bg="#ffffff", bd=0, activebackground="#333", command=lambda: self.tampilkan_menu_overlay("visualisasi")).place(x=20, y=170, width=40, height=40)
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
        
        # Start background check loops
        self.periksa_pembaruan_database()
        self.periksa_pengingat_tugas()

    def hapus_placeholder(self, event):
        if self.entry_input.get() == self.placeholder_text:
            self.entry_input.delete(0, tk.END)
            self.entry_input.config(fg="white")

    def tambah_placeholder(self, event):
        if not self.entry_input.get():
            self.entry_input.insert(0, self.placeholder_text)
            self.entry_input.config(fg="gray")

    def run_video_thread(self):
        import time
        while self.video_thread_running:
            if not self.update_video_active:
                time.sleep(0.05)
                continue
                
            # Mencegah pembacaan/decoding video jika antrean masih penuh (hemat CPU)
            if self.video_queue.full():
                time.sleep(0.01)
                continue
                
            ret = False
            frame = None
            
            if self.playing_intro:
                ret, frame = self.cap_intro.read()
                if not ret:
                    self.intro_finished = True
                    ret, frame = self.cap_bg.read()
            else:
                ret, frame = self.cap_bg.read()
                if not ret:
                    self.cap_bg.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = self.cap_bg.read()
                    
            if ret:
                # OPTIMISASI UTAMA: Gunakan OpenCV C++ untuk resize (jauh lebih cepat daripada PIL)
                frame_resized = cv2.resize(frame, (1280, 720), interpolation=cv2.INTER_LINEAR)
                frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                frame_pil = Image.fromarray(frame_rgb)
                try:
                    self.video_queue.put(frame_pil, block=False)
                except queue.Full:
                    pass
                time.sleep(0.03)
            else:
                time.sleep(0.01)

    def keluar_aplikasi(self):
        self.video_thread_running = False
        self.update_video_active = False
        try:
            self.cap_intro.release()
            self.cap_bg.release()
        except:
            pass
        try:
            if hasattr(self, 'tray_icon'):
                self.tray_icon.stop()
        except:
            pass
        self.root.quit()
        self.root.destroy()

    def setup_system_tray(self):
        import pystray
        from pystray import MenuItem as item
        
        # Load logo for system tray icon
        try:
            self.tray_image = Image.open(r"dump req\AmadeusLogo.png").resize((64, 64))
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal memuat logo tray: {e}")
            self.tray_image = Image.new("RGBA", (64, 64), (26, 26, 26, 255))
            
        # Definisikan menu klik kanan
        menu = pystray.Menu(
            item('Tampilkan Amadeus (Restore)', self.tray_restore),
            item('Sembunyikan Amadeus (Minimize)', self.tray_minimize),
            item('Keluar (Exit)', self.tray_exit)
        )
        
        self.tray_icon = pystray.Icon("Amadeus VN", self.tray_image, "Amadeus System", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def tray_restore(self, icon=None, item=None):
        self.root.after(0, self.restore_main_window)
        
    def tray_minimize(self, icon=None, item=None):
        self.root.after(0, self.sembunyikan_ke_tray)
        
    def tray_exit(self, icon=None, item=None):
        self.root.after(0, self.keluar_aplikasi)

    def update_video_frame(self):
        if not self.update_video_active:
            return
            
        if hasattr(self, 'intro_finished') and self.intro_finished and self.playing_intro:
            self.skip_intro()
            
        try:
            frame_pil = self.video_queue.get_nowait()
            self.current_frame_tk = ImageTk.PhotoImage(frame_pil)
            self.canvas.itemconfig(self.vid_img_on_canvas, image=self.current_frame_tk)
        except queue.Empty:
            pass
            
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
            ("visualisasi", "📊 Visualisasi"),
            ("tugas", "⏰ Pengingat"),
            ("catatan", "📝 Catatan"),
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
        elif tab_name == "visualisasi":
            self.render_tab_visualisasi()
        elif tab_name == "tugas":
            self.render_tab_tugas()
        elif tab_name == "catatan":
            self.render_tab_catatan()
        elif tab_name == "log":
            self.render_tab_log()
        elif tab_name == "settings":
            self.render_tab_settings()

    def render_tab_visualisasi(self):
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
        from datetime import datetime
        
        # Judul Tab
        lbl_title = tk.Label(self.content_frame, text="Analisis & Visualisasi Finansial Amadeus", 
                             font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
        lbl_title.pack(anchor="w", padx=15, pady=(15, 5))
        
        records = ambil_riwayat_transaksi()
        if not records:
            lbl_empty = tk.Label(self.content_frame, text="Belum ada data transaksi untuk divisualisasikan.", 
                                 font=("Consolas", 12, "italic"), bg="#1a1a1a", fg="gray")
            lbl_empty.pack(expand=True)
            return

        # 1. Olah data kategori pengeluaran (Pie Chart)
        kategori_pengeluaran = {}
        for _, _, jns, nom, kat, _ in records:
            if jns.lower() == 'pengeluaran':
                kategori_pengeluaran[kat] = kategori_pengeluaran.get(kat, 0) + nom
                
        # 2. Olah data tren saldo kumulatif (Line Chart)
        chronological_records = sorted(records, key=lambda x: x[1]) # urut tanggal ascending
        dates = []
        balances = []
        current_balance = 0
        
        for _, tgl, jns, nom, _, _ in chronological_records:
            if jns.lower() == 'pemasukan':
                current_balance += nom
            else:
                current_balance -= nom
                
            try:
                dt = datetime.strptime(tgl, '%Y-%m-%d %H:%M:%S')
                tgl_fmt = dt.strftime('%m-%d %H:%M')
            except:
                tgl_fmt = tgl[:16]
                
            dates.append(tgl_fmt)
            balances.append(current_balance)

        # 3. Membuat Figure Matplotlib bertema gelap
        fig = plt.Figure(figsize=(7.8, 3.8), facecolor='#1a1a1a')
        
        # Subplot 1: Pie Chart Pengeluaran
        ax1 = fig.add_subplot(121)
        if kategori_pengeluaran:
            labels = list(kategori_pengeluaran.keys())
            sizes = list(kategori_pengeluaran.values())
            colors = ['#00ffcc', '#ff3366', '#33ccff', '#ffcc00', '#9933ff', '#ff9900']
            
            wedges, texts, autotexts = ax1.pie(
                sizes, labels=labels, autopct='%1.1f%%', startangle=90, 
                colors=colors[:len(labels)], textprops=dict(color="w", fontsize=8)
            )
            for text in texts:
                text.set_color("w")
                text.set_fontname("Consolas")
            for autotext in autotexts:
                autotext.set_fontsize(8)
                autotext.set_weight('bold')
                autotext.set_fontname("Consolas")
                
            ax1.set_title("Kategori Pengeluaran", color='white', fontname='Consolas', fontsize=11, fontweight='bold')
        else:
            ax1.text(0.5, 0.5, "Tidak ada data\npengeluaran", color='gray', ha='center', va='center', fontname='Consolas', fontsize=10)
            ax1.axis('off')
            
        # Subplot 2: Line Chart Tren Saldo
        ax2 = fig.add_subplot(122)
        if dates:
            ax2.plot(dates, balances, color='#00ffcc', marker='o', markersize=3, linewidth=1.5, label='Saldo')
            ax2.fill_between(dates, balances, color='#00ffcc', alpha=0.1)
            ax2.set_title("Tren Saldo Kumulatif", color='white', fontname='Consolas', fontsize=11, fontweight='bold')
            ax2.set_facecolor('#111111')
            ax2.tick_params(colors='white', labelsize=8)
            ax2.grid(True, color='#333333', linestyle='--', linewidth=0.5)
            
            for tick in ax2.get_xticklabels():
                tick.set_rotation(25)
                tick.set_fontname('Consolas')
            for tick in ax2.get_yticklabels():
                tick.set_fontname('Consolas')
                
            ax2.xaxis.set_major_locator(ticker.MaxNLocator(5))
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'Rp {int(x):,}'))
        else:
            ax2.text(0.5, 0.5, "Tidak ada data\ntransaksi", color='gray', ha='center', va='center', fontname='Consolas', fontsize=10)
            ax2.axis('off')
            
        fig.tight_layout()
        
        # Embed Figure ke widget Tkinter
        canvas = FigureCanvasTkAgg(fig, master=self.content_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        canvas_widget.config(bg="#1a1a1a")

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

        # --- SEKTOR 1B: VOLUME SUARA ---
        lbl_volume = tk.Label(self.content_frame, text="Volume Suara Kurisu & Musik (%):", 
                              font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
        lbl_volume.pack(anchor="w", padx=20, pady=(5, 0))
        
        volume_slider = tk.Scale(self.content_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                                 bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                                 activebackground="#00ffcc")
        volume_slider.set(int(self.voice_volume * 100))
        volume_slider.pack(anchor="w", padx=20, pady=(0, 10))

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
            
            # 3. Simpan volume suara
            vol_value = volume_slider.get()
            self.voice_volume = vol_value / 100.0
            pygame.mixer.music.set_volume(self.voice_volume)
            for snd in self.sound_cache.values():
                snd.set_volume(self.voice_volume)
            
            # 4. Simpan mode AI
            mode_terpilih = self.var_ai_mode.get()
            
            # 5. Tulis ke file amadeus_config.json
            cfg_data = {
                "typing_speed": self.typing_speed,
                "voice_volume": vol_value,
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
        else:
            # Fallback analisis sentimen / kata kunci jika AI lupa menyertakan tag emosi
            text_lower = balasan.lower()
            
            # 1. Blushing/Tsundere (gagap, malu, istri, kangen, sayang, tidak suka/malu)
            # Pola gagap: I-Istri, S-siapa, d-dia, b-bukan, m-memangnya
            pola_gagap = re.search(r'\b([a-zA-Z])-\1', text_lower)
            if pola_gagap or any(kw in text_lower for kw in ["istri", "suami", "pacar", "kangen", "merindukan", "malu", "tsundere", "blush", "sayang", "b-bukan", "h-hanya"]):
                mood_terdeteksi = "blushing_tsundere"
            # 2. Mad/Angry
            elif any(kw in text_lower for kw in ["marah", "benci", "kesal", "menyebalkan", "berisik", "bodoh", "baka", "jangan", "kasar"]):
                mood_terdeteksi = "mad"
            # 3. Smiling/Happy
            elif any(kw in text_lower for kw in ["senang", "terima kasih", "makasih", "hebat", "bagus", "haha", "hehe", "smile"]):
                mood_terdeteksi = "smiling"
            # 4. Thinking
            elif any(kw in text_lower for kw in ["pikir", "memikirkan", "analisis", "sepertinya", "mungkin", "rasanya", "kalkulasi", "data", "entahlah"]):
                mood_terdeteksi = "thinking"
            # 5. Look Away/Hesitant
            elif any(kw in text_lower for kw in ["ragu", "anu", "aduh", "bagaimana ya", "sulit"]):
                mood_terdeteksi = "look_away"
            
        return mood_terdeteksi, balasan

    def play_voice_sfx(self, mood):
        import os
        import random
        
        voice_dir = r"dump req\voice_barks"
        
        voice_pools = {
            "normal": ["CRS_0141.wav", "CRS_0144.wav", "CRS_0159.wav", "CRS_0242.wav", "CRS_0058.wav", "CRS_0083.wav"],
            "mad": ["CRS_0158.wav", "CRS_0172.wav", "CRS_0200.wav", "CRS_0133.wav", "CRS_0121.wav"],
            "smiling": ["CRS_0141.wav", "CRS_0159.wav", "CRS_0242.wav", "CRS_0182.wav", "CRS_0183.wav"],
            "thinking": ["CRS_0119.wav", "CRS_0185.wav", "CRS_0247.wav", "CRS_0027angry.wav", "CRS_0193.wav", "CRS_0145.wav", "CRS_0036shy.wav"],
            "look_away": ["CRS_0172.wav", "CRS_0200.wav", "CRS_0207.wav", "CRS_0209.wav", "CRS_0139.wav"],
            "blushing_tsundere": ["CRS_0158.wav", "CRS_0148.wav", "CRS_0175.wav", "CRS_0207.wav"]
        }
        
        fallback_files = {
            "normal": r"dump req\voice_normal.wav",
            "mad": r"dump req\voice_mad.wav",
            "smiling": r"dump req\voice_smiling.wav",
            "thinking": r"dump req\voice_thinking.wav",
            "look_away": r"dump req\voice_look_away.wav",
            "blushing_tsundere": r"dump req\voice_blushing_tsundere.wav"
        }
        
        file_path = None
        if mood in voice_pools:
            selected_file = random.choice(voice_pools[mood])
            full_path = os.path.join(voice_dir, selected_file)
            if os.path.exists(full_path):
                file_path = full_path
                
        if not file_path and mood in fallback_files:
            file_path = fallback_files[mood]
            
        if file_path and os.path.exists(file_path):
            try:
                pygame.mixer.stop()
                if file_path in self.sound_cache:
                    voice_sound = self.sound_cache[file_path]
                else:
                    print(f"[SYSTEM LOG] Caching sound: {file_path}")
                    voice_sound = pygame.mixer.Sound(file_path)
                    self.sound_cache[file_path] = voice_sound
                voice_sound.set_volume(self.voice_volume)
                voice_sound.play()
            except Exception as e:
                print(f"[SYSTEM LOG] Gagal memutar suara Kurisu ({mood}): {e}")
 
    def play_specific_voice(self, filename):
        import os
        voice_dir = r"dump req\voice_barks"
        file_path = os.path.join(voice_dir, filename)
        if os.path.exists(file_path):
            try:
                pygame.mixer.stop()
                if file_path in self.sound_cache:
                    voice_sound = self.sound_cache[file_path]
                else:
                    print(f"[SYSTEM LOG] Caching sound: {file_path}")
                    voice_sound = pygame.mixer.Sound(file_path)
                    self.sound_cache[file_path] = voice_sound
                voice_sound.set_volume(self.voice_volume)
                voice_sound.play()
            except Exception as e:
                print(f"[SYSTEM LOG] Gagal memutar suara spesifik ({filename}): {e}")

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
        # Memastikan sprite dimuat secara malas (lazy loading) jika belum ada
        self.get_sprite(target_mood)
        
        if target_mood not in self.pil_sprites:
            return
            
        self.play_voice_sfx(target_mood)
        
        if target_mood != self.current_mood:
            self.current_mood = target_mood
            
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
        self.root.after(0, lambda: (self.vn_text.config(text=loading_text), self.vn_name.config(text="Amadeus")))
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

    def start_telegram_bot_thread(self):
        import threading
        def run_bot():
            import telegram_bot
            try:
                telegram_bot.main()
            except Exception as e:
                print(f"[SYSTEM LOG] Gagal menjalankan Telegram Bot di background thread: {e}")
        
        # Start bot in background daemon thread
        threading.Thread(target=run_bot, daemon=True).start()

    def trim_memory(self):
        try:
            import gc
            # 1. Bersihkan antrean video agar tidak menyimpan frame mentah di memori
            while not self.video_queue.empty():
                try:
                    self.video_queue.get_nowait()
                except:
                    break
            
            # 2. Panggil garbage collector
            gc.collect()
            
            # 3. Lepaskan kelebihan working set kembali ke Windows OS
            import ctypes
            k32 = ctypes.windll.kernel32
            k32.GetCurrentProcess.restype = ctypes.c_void_p
            k32.SetProcessWorkingSetSize.argtypes = [ctypes.c_void_p, ctypes.c_size_t, ctypes.c_size_t]
            h = k32.GetCurrentProcess()
            k32.SetProcessWorkingSetSize(h, ctypes.c_size_t(-1).value, ctypes.c_size_t(-1).value)
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal memangkas RAM: {e}")

    def sembunyikan_ke_tray(self):
        self.update_video_active = False # Hentikan rendering video di background
        self.root.withdraw() # Sembunyikan window utama GUI ke system tray
        self.trim_memory() # Pangkas working set RAM
        print("[SYSTEM LOG] Amadeus disembunyikan ke System Tray (Video paused & RAM dipangkas).")

        self.update_video_frame() # Mulai kembali rendering video background
        print("[SYSTEM LOG] Amadeus GUI dipulihkan.")

    def render_tab_tugas(self):
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

        # Container Frame Kiri (Form Input) dan Kanan (Tabel)
        main_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- SEKTOR KIRI: FORM INPUT ---
        left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_frame.pack_propagate(False)

        lbl_form_title = tk.Label(left_frame, text="Tambah Pengingat", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="#00ffcc")
        lbl_form_title.pack(anchor="w", pady=(0, 10))

        lbl_waktu = tk.Label(left_frame, text="Waktu (HH:MM / YYYY-MM-DD HH:MM):", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
        lbl_waktu.pack(anchor="w", pady=(5, 2))

        # Default placeholder: waktu sekarang + 10 menit
        from datetime import datetime, timedelta
        placeholder_waktu = (datetime.now() + timedelta(minutes=10)).strftime('%H:%M')
        self.entry_tugas_waktu = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
        self.entry_tugas_waktu.pack(fill=tk.X, pady=(0, 10))
        self.entry_tugas_waktu.insert(0, placeholder_waktu)

        lbl_desc = tk.Label(left_frame, text="Deskripsi Tugas / Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
        lbl_desc.pack(anchor="w", pady=(5, 2))

        self.entry_tugas_desc = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
        self.entry_tugas_desc.pack(fill=tk.X, pady=(0, 15))

        lbl_error_tugas = tk.Label(left_frame, text="", font=("Consolas", 8), bg="#1a1a1a", fg="#ff4444", wraplength=230, justify=tk.LEFT)
        lbl_error_tugas.pack(fill=tk.X, pady=5)

        def simpan_tugas_baru():
            waktu_val = self.entry_tugas_waktu.get().strip()
            desc_val = self.entry_tugas_desc.get().strip()
            
            if not waktu_val or not desc_val:
                lbl_error_tugas.config(text="* Waktu dan deskripsi wajib diisi!", fg="#ff4444")
                return
                
            # Validasi format waktu
            import re
            is_valid_format = False
            # Format 1: HH:MM
            if re.match(r'^\d{2}:\d{2}$', waktu_val):
                is_valid_format = True
            # Format 2: YYYY-MM-DD HH:MM
            elif re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}$', waktu_val):
                is_valid_format = True
                
            if not is_valid_format:
                lbl_error_tugas.config(text="* Format salah! Gunakan HH:MM (contoh: 15:30) atau YYYY-MM-DD HH:MM (contoh: 2026-06-15 15:30)", fg="#ff4444")
                return
                
            import core
            if core.tambah_tugas(waktu_val, desc_val, "desktop"):
                self.log_history.append(f"[SYSTEM]\nPengingat disimpan: '{desc_val}' pada {waktu_val}.")
                self.render_tab_tugas() # Re-render tab to update list
            else:
                lbl_error_tugas.config(text="* Gagal menyimpan ke database.", fg="#ff4444")

        btn_tambah = tk.Button(left_frame, text="🔔 Tambah Pengingat", font=("Consolas", 9, "bold"),
                               bg="#115e59", fg="white", activebackground="#14b8a6", activeforeground="white",
                               relief=tk.FLAT, command=simpan_tugas_baru, pady=8)
        btn_tambah.pack(fill=tk.X, side=tk.BOTTOM)

        # --- SEKTOR KANAN: TABEL DAFTAR TUGAS ---
        right_frame = tk.Frame(main_frame, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        lbl_table_title = tk.Label(right_frame, text="Daftar Pengingat Aktif", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="white")
        lbl_table_title.pack(anchor="w", pady=(0, 10))

        # Setup Table columns
        cols = ("ID", "Waktu", "Deskripsi", "Status", "Sumber")
        self.tree_tugas = ttk.Treeview(right_frame, columns=cols, show="headings", style="Custom.Treeview")
        
        scroll = ttk.Scrollbar(right_frame, orient="vertical", command=self.tree_tugas.yview)
        self.tree_tugas.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_tugas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree_tugas.heading("ID", text="ID")
        self.tree_tugas.heading("Waktu", text="Waktu")
        self.tree_tugas.heading("Deskripsi", text="Deskripsi")
        self.tree_tugas.heading("Status", text="Status")
        self.tree_tugas.heading("Sumber", text="Sumber")

        self.tree_tugas.column("ID", width=40, minwidth=30, anchor=tk.CENTER)
        self.tree_tugas.column("Waktu", width=120, minwidth=100, anchor=tk.CENTER)
        self.tree_tugas.column("Deskripsi", width=180, minwidth=150, anchor=tk.W)
        self.tree_tugas.column("Status", width=80, minwidth=60, anchor=tk.CENTER)
        self.tree_tugas.column("Sumber", width=70, minwidth=60, anchor=tk.CENTER)

        self.tree_tugas.tag_configure("aktif", foreground="#00ffcc")
        self.tree_tugas.tag_configure("selesai", foreground="gray")
        self.tree_tugas.tag_configure("lewat", foreground="#ff4444")

        # Load data to table
        import core
        tugas_list = core.ambil_semua_tugas()
        for t_id, waktu, desc, status, sumber in tugas_list:
            self.tree_tugas.insert("", tk.END, values=(t_id, waktu, desc, status.upper(), sumber.upper()), tags=(status,))

        # Control Frame di bawah tabel
        control_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(0, 15))

        def selesaikan_tugas_terpilih():
            selected = self.tree_tugas.selection()
            if not selected: return
            item_values = self.tree_tugas.item(selected[0], "values")
            t_id = int(item_values[0])
            if core.update_status_tugas(t_id, 'selesai'):
                self.log_history.append(f"[SYSTEM]\nPengingat ID {t_id} selesai.")
                self.render_tab_tugas()

        def hapus_tugas_terpilih():
            selected = self.tree_tugas.selection()
            if not selected: return
            item_values = self.tree_tugas.item(selected[0], "values")
            t_id = int(item_values[0])
            if core.hapus_tugas(t_id):
                self.log_history.append(f"[SYSTEM]\nPengingat ID {t_id} dihapus.")
                self.render_tab_tugas()

        btn_selesai = tk.Button(control_frame, text="✓ Selesai", font=("Consolas", 9, "bold"),
                                bg="#1e293b", fg="white", activebackground="#334155", activeforeground="white",
                                relief=tk.FLAT, command=selesaikan_tugas_terpilih, padx=10, pady=5)
        btn_selesai.pack(side=tk.RIGHT, padx=5)

        btn_hapus = tk.Button(control_frame, text="Hapus", font=("Consolas", 9, "bold"),
                              bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                              relief=tk.FLAT, command=hapus_tugas_terpilih, padx=10, pady=5)
        btn_hapus.pack(side=tk.RIGHT, padx=5)

    def periksa_pembaruan_database(self):
        try:
            import sqlite3
            import core
            conn = sqlite3.connect('amadeus_finansial.db')
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*), MAX(id) FROM transaksi")
            state = cursor.fetchone()
            conn.close()
            
            if hasattr(self, 'last_db_state') and self.last_db_state != state:
                self.last_db_state = state
                saldo_baru = core.hitung_saldo()
                self.label_saldo.config(text=f"Saldo: Rp {saldo_baru:,}")
                if self.active_tab == "transaksi":
                    self.render_tab_transaksi()
                elif self.active_tab == "visualisasi":
                    self.render_tab_visualisasi()
            elif not hasattr(self, 'last_db_state'):
                self.last_db_state = state
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal memeriksa update DB: {e}")
            
        self.root.after(2000, self.periksa_pembaruan_database)

    def periksa_pengingat_tugas(self):
        try:
            from datetime import datetime
            import core
            sekarang = datetime.now()
            sekarang_str_full = sekarang.strftime('%Y-%m-%d %H:%M')
            sekarang_str_time = sekarang.strftime('%H:%M')

            tugas_list = core.ambil_semua_tugas()
            for t_id, waktu, deskripsi, status, sumber in tugas_list:
                if status == 'aktif':
                    waktu_cocok = False
                    if len(waktu) == 16:  # YYYY-MM-DD HH:MM
                        waktu_cocok = (waktu == sekarang_str_full)
                    elif len(waktu) == 5:  # HH:MM
                        waktu_cocok = (waktu == sekarang_str_time)
                        
                    if waktu_cocok:
                        # Tandai status tugas lewat di DB
                        core.update_status_tugas(t_id, 'lewat')
                        
                        # 1. Mainkan suara alert
                        self.play_specific_voice("CRS_0119.wav")
                        
                        # 2. Tampilkan alarm visual di desktop
                        self.tunjukkan_alarm_desktop(deskripsi, waktu)
                        
                        # 3. Kirim notifikasi ke Telegram
                        panggilan = core.dapatkan_panggilan_user()
                        panggilan_str = f" {panggilan}" if panggilan else ""
                        msg = f"⏰ *[PENGINGAT ALARM AMADEUS]*\nHalo{panggilan_str}! Saatnya melakukan:\n👉 *{deskripsi}* (Waktu: {waktu})"
                        import threading
                        threading.Thread(target=core.kirim_notifikasi_telegram, args=(msg,), daemon=True).start()
                        
                        # Refresh tab tugas jika sedang terbuka
                        if self.active_tab == "tugas":
                            self.render_tab_tugas()
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal memeriksa pengingat tugas: {e}")
            
        self.root.after(15000, self.periksa_pengingat_tugas)

    def tununjukkan_alarm_desktop(self, deskripsi, waktu):
        # Tampilkan alarm visual di desktop
        if not self.update_video_active:
            self.restore_main_window()
            
        # Glitch ke pose berpikir
        if "thinking" in self.sprites:
            self.trigger_glitch_transition("thinking")
            
        panggilan = core.dapatkan_panggilan_user()
        panggilan_str = f", {panggilan}" if panggilan else ""
        teks_alert = f"Halo{panggilan_str}! Waktu sudah menunjukkan pukul {waktu}. Saatnya melakukan tugasmu: '{deskripsi}'. Jangan ditunda-tunda ya!"
        
        # Tutup menu overlay agar dialog VN terlihat jelas
        self.tutup_menu_overlay()
        
        # Tampilkan teks VN dengan efek ketik
        self.vn_name.config(text="Amadeus (Alarm)")
        self.vn_text.config(text="")
        self.tampilkan_balasan(teks_alert)

    def render_tab_catatan(self):
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

        # Split pane kiri (input form) dan kanan (tabel list & detail reader)
        main_frame = tk.Frame(self.content_frame, bg="#1a1a1a")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

        # --- SEKTOR KIRI: FORM INPUT ---
        left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left_frame.pack_propagate(False)

        lbl_form_title = tk.Label(left_frame, text="Buat Catatan Baru", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="#00ffcc")
        lbl_form_title.pack(anchor="w", pady=(0, 10))

        lbl_judul = tk.Label(left_frame, text="Judul Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
        lbl_judul.pack(anchor="w", pady=(5, 2))

        self.entry_note_judul = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
        self.entry_note_judul.pack(fill=tk.X, pady=(0, 10))

        lbl_konten = tk.Label(left_frame, text="Isi Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
        lbl_konten.pack(anchor="w", pady=(5, 2))

        # Text area untuk multi-line note content
        self.txt_note_konten = tk.Text(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 9), insertbackground="white", height=10, relief=tk.FLAT)
        self.txt_note_konten.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

        lbl_error_note = tk.Label(left_frame, text="", font=("Consolas", 8), bg="#1a1a1a", fg="#ff4444", wraplength=230, justify=tk.LEFT)
        lbl_error_note.pack(fill=tk.X, pady=5)

        def simpan_catatan_baru():
            judul_val = self.entry_note_judul.get().strip()
            konten_val = self.txt_note_konten.get("1.0", tk.END).strip()
            
            if not konten_val:
                lbl_error_note.config(text="* Isi catatan tidak boleh kosong!", fg="#ff4444")
                return
                
            if not judul_val:
                # Judul otomatis dari baris pertama
                words = konten_val.split()
                judul_val = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
                
            import core
            if core.tambah_catatan(judul_val, konten_val, "desktop"):
                self.log_history.append(f"[SYSTEM]\nCatatan disimpan: '{judul_val}'.")
                self.render_tab_catatan() # Re-render to update
            else:
                lbl_error_note.config(text="* Gagal menyimpan ke database.", fg="#ff4444")

        btn_tambah = tk.Button(left_frame, text="📝 Simpan Catatan", font=("Consolas", 9, "bold"),
                               bg="#115e59", fg="white", activebackground="#14b8a6", activeforeground="white",
                               relief=tk.FLAT, command=simpan_catatan_baru, pady=8)
        btn_tambah.pack(fill=tk.X, side=tk.BOTTOM)

        # --- SEKTOR KANAN: LIST TABEL & PRATINJAU CATATAN ---
        right_frame = tk.Frame(main_frame, bg="#1a1a1a")
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Split kanan atas (tabel list) dan kanan bawah (preview/baca)
        top_right = tk.Frame(right_frame, bg="#1a1a1a", height=180)
        top_right.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        top_right.pack_propagate(False)

        lbl_table_title = tk.Label(top_right, text="Daftar Catatan Tersimpan", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="white")
        lbl_table_title.pack(anchor="w", pady=(0, 5))

        # Setup Table columns
        cols = ("ID", "Tanggal", "Judul", "Sumber")
        self.tree_notes = ttk.Treeview(top_right, columns=cols, show="headings", style="Custom.Treeview")
        
        scroll = ttk.Scrollbar(top_right, orient="vertical", command=self.tree_notes.yview)
        self.tree_notes.configure(yscrollcommand=scroll.set)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree_notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tree_notes.heading("ID", text="ID")
        self.tree_notes.heading("Tanggal", text="Tanggal")
        self.tree_notes.heading("Judul", text="Judul Catatan")
        self.tree_notes.heading("Sumber", text="Sumber")

        self.tree_notes.column("ID", width=40, minwidth=30, anchor=tk.CENTER)
        self.tree_notes.column("Tanggal", width=130, minwidth=110, anchor=tk.CENTER)
        self.tree_notes.column("Judul", width=200, minwidth=150, anchor=tk.W)
        self.tree_notes.column("Sumber", width=70, minwidth=60, anchor=tk.CENTER)

        # Load data to table
        import core
        catatan_list = core.ambil_semua_catatan()
        for c_id, tgl, judul, konten, sumber in catatan_list:
            self.tree_notes.insert("", tk.END, values=(c_id, tgl, judul, sumber.upper()))

        # Sektor kanan bawah (Detail Catatan)
        bottom_right = tk.Frame(right_frame, bg="#1a1a1a")
        bottom_right.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(10, 0))

        lbl_preview_title = tk.Label(bottom_right, text="Isi Catatan Detail", font=("Consolas", 10, "bold"), bg="#1a1a1a", fg="#00ffcc")
        lbl_preview_title.pack(anchor="w", pady=(0, 5))

        # Text area pratinjau yang read-only
        self.txt_note_preview = scrolledtext.ScrolledText(bottom_right, bg="#111111", fg="#e0e0e0", font=("Consolas", 10), wrap=tk.WORD, bd=0, highlightthickness=0, height=8)
        self.txt_note_preview.pack(fill=tk.BOTH, expand=True)
        self.txt_note_preview.config(state=tk.DISABLED)

        # Fungsi pengisian detail otomatis saat baris tabel diklik
        def tampilkan_detail_catatan(event):
            selected = self.tree_notes.selection()
            if not selected: return
            item_values = self.tree_notes.item(selected[0], "values")
            c_id = int(item_values[0])
            
            # Cari isi konten catatan dari data
            target_catatan = next((c for c in catatan_list if c[0] == c_id), None)
            if target_catatan:
                _, _, _, konten, _ = target_catatan
                self.txt_note_preview.config(state=tk.NORMAL)
                self.txt_note_preview.delete("1.0", tk.END)
                self.txt_note_preview.insert(tk.END, konten)
                self.txt_note_preview.config(state=tk.DISABLED)

        self.tree_notes.bind("<<TreeviewSelect>>", tampilkan_detail_catatan)

        # Action Buttons di bawah detail area
        action_frame = tk.Frame(bottom_right, bg="#1a1a1a")
        action_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

        def hapus_catatan_terpilih():
            selected = self.tree_notes.selection()
            if not selected: return
            item_values = self.tree_notes.item(selected[0], "values")
            c_id = int(item_values[0])
            import core
            if core.hapus_catatan(c_id):
                self.log_history.append(f"[SYSTEM]\nCatatan ID {c_id} dihapus.")
                self.render_tab_catatan()

        btn_hapus_note = tk.Button(action_frame, text="Hapus Catatan Terpilih", font=("Consolas", 9, "bold"),
                                   bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                                   relief=tk.FLAT, command=hapus_catatan_terpilih, padx=10, pady=5)
        btn_hapus_note.pack(side=tk.RIGHT)

if __name__ == "__main__":
    root = tk.Tk()
    app = AmadeusVN(root)
    root.mainloop()