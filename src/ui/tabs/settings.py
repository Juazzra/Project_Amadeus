import tkinter as tk
import core
from core import load_config, save_config, hitung_saldo

def render_tab_settings(vn_app):
    cfg = load_config()
    
    # Judul Tab (Fixed / Tetap di atas)
    lbl_title = tk.Label(vn_app.content_frame, text="Amadeus Settings & Configuration", 
                         font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
    lbl_title.pack(anchor="w", padx=15, pady=(10, 10))

    # --- SETUP CANVAS SCROLLBAR ---
    container = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    container.pack(fill=tk.BOTH, expand=True)

    canvas = tk.Canvas(container, bg="#1a1a1a", highlightthickness=0)
    scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#1a1a1a")

    scrollbar.pack(side="right", fill="y")
    canvas.pack(side="left", fill="both", expand=True)
    canvas.configure(yscrollcommand=scrollbar.set)

    # Configure scrollregion on resize
    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(
            scrollregion=canvas.bbox("all")
        )
    )

    # Stretch scrollable_frame to match canvas width
    canvas_frame_window = canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")

    def _configure_canvas_window(event):
        canvas.itemconfig(canvas_frame_window, width=event.width)
        
    canvas.bind("<Configure>", _configure_canvas_window)

    # Bind Mousewheel safely when mouse enters/leaves settings form area
    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def _bind_mouse(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    def _unbind_mouse(event):
        canvas.unbind_all("<MouseWheel>")
        
    canvas.bind("<Enter>", _bind_mouse)
    canvas.bind("<Leave>", _unbind_mouse)

    # --- SEKTOR 1: KECEPATAN TEKS ---
    lbl_speed = tk.Label(scrollable_frame, text="Text Typing Speed (ms/character):", 
                         font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_speed.pack(anchor="w", padx=20)
    
    speed_slider = tk.Scale(scrollable_frame, from_=10, to=150, orient=tk.HORIZONTAL, 
                            bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                            activebackground="#00ffcc")
    speed_slider.set(vn_app.typing_speed)
    speed_slider.pack(anchor="w", padx=20, pady=(0, 10))

    # --- SEKTOR 1B: VOLUME SUARA ---
    lbl_volume = tk.Label(scrollable_frame, text="Volume Suara Kurisu & Musik (%):", 
                          font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_volume.pack(anchor="w", padx=20, pady=(5, 0))
    
    volume_slider = tk.Scale(scrollable_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                             bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                             activebackground="#00ffcc")
    volume_slider.set(int(vn_app.voice_volume * 100))
    volume_slider.pack(anchor="w", padx=20, pady=(0, 10))

    # --- SEKTOR 2: PEMILIHAN OTAK AI ---
    lbl_brain = tk.Label(scrollable_frame, text="AI Brain Source (Mode AI):", 
                         font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_brain.pack(anchor="w", padx=20)
    
    core_mode = core.MODE_AI_AKTIF
    if core_mode == "cloud":
        core_mode = "cloud_2_5"
    vn_app.var_ai_mode = tk.StringVar(value=core_mode)
    
    frame_radio = tk.Frame(scrollable_frame, bg="#1a1a1a")
    frame_radio.pack(anchor="w", padx=20, pady=5)

    r_local = tk.Radiobutton(frame_radio, text="Lokal (Ollama)", variable=vn_app.var_ai_mode, value="local", 
                            bg="#1a1a1a", fg="#00ffcc", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                            activeforeground="#00ffcc", font=("Consolas", 10))
    r_local.pack(side=tk.LEFT, padx=(0, 15))
    
    r_cloud_2_5 = tk.Radiobutton(frame_radio, text="Gemini 3.1 Lite", variable=vn_app.var_ai_mode, value="cloud_2_5", 
                                bg="#1a1a1a", fg="#ffcc00", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                activeforeground="#ffcc00", font=("Consolas", 10))
    r_cloud_2_5.pack(side=tk.LEFT, padx=(0, 15))

    r_cloud_3_5 = tk.Radiobutton(frame_radio, text="Gemini 3.5", variable=vn_app.var_ai_mode, value="cloud_3_5", 
                                bg="#1a1a1a", fg="#e11d48", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                activeforeground="#e11d48", font=("Consolas", 10))
    r_cloud_3_5.pack(side=tk.LEFT)

    lbl_warning = tk.Label(scrollable_frame, text="*Mengubah mode otak akan mereset ingatan sesi aktif Amadeus.", 
                           font=("Consolas", 8, "italic"), bg="#1a1a1a", fg="gray")
    lbl_warning.pack(anchor="w", padx=20, pady=(0, 5))

    # --- SEKTOR 2B: RESPON TELEGRAM DI DESKTOP ---
    vn_app.var_sync_tele = tk.BooleanVar(value=cfg.get("sync_telegram_response", False))
    chk_sync_tele = tk.Checkbutton(scrollable_frame, text="React to Telegram chats on desktop overlay",
                                   variable=vn_app.var_sync_tele, bg="#1a1a1a", fg="#00ffcc",
                                   selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                   activeforeground="#00ffcc", font=("Consolas", 10),
                                   highlightthickness=0, bd=0)
    chk_sync_tele.pack(anchor="w", padx=20, pady=(5, 10))

    # --- SEKTOR 3: MEMORI USER (TENTANG SAYA) ---
    lbl_memory = tk.Label(scrollable_frame, text="User Memory (Informasi Tentang Saya):", 
                          font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_memory.pack(anchor="w", padx=20, pady=(5, 2))
    
    user_mem = cfg.get("user_memory", "")
    
    vn_app.txt_memory = tk.Text(scrollable_frame, bg="#111111", fg="white", 
                              font=("Consolas", 9), insertbackground="white", 
                              height=3, width=70, relief=tk.FLAT)
    vn_app.txt_memory.pack(anchor="w", padx=20, pady=(0, 5))
    vn_app.txt_memory.insert(tk.END, user_mem)

    # Label status keberhasilan
    lbl_status = tk.Label(scrollable_frame, text="", font=("Consolas", 10, "bold"), bg="#1a1a1a")
    lbl_status.pack(anchor="w", padx=20, pady=2)

    # --- TOMBOL SIMPAN ---
    def simpan_setting_hybrid():
        # 1. Ambil teks memori dari Text widget
        user_mem_value = vn_app.txt_memory.get("1.0", tk.END).strip()
        
        # 2. Simpan kecepatan teks
        vn_app.typing_speed = speed_slider.get()
        
        # 3. Simpan volume suara
        vol_value = volume_slider.get()
        vn_app.voice_volume = vol_value / 100.0
        if getattr(vn_app, 'audio_enabled', True):
            import pygame
            try:
                pygame.mixer.music.set_volume(vn_app.voice_volume)
                for snd in vn_app.sound_cache.values():
                    snd.set_volume(vn_app.voice_volume)
            except Exception as e:
                print(f"[SYSTEM LOG] Gagal menyetel volume audio: {e}")
        
        # 4. Simpan mode AI
        mode_terpilih = vn_app.var_ai_mode.get()
        
        # 4B. Simpan toggle respon telegram
        sync_tele_value = vn_app.var_sync_tele.get()
        vn_app.sync_telegram_response = sync_tele_value
        
        # 5. Tulis ke file amadeus_config.json
        cfg_data = {
            "typing_speed": vn_app.typing_speed,
            "voice_volume": vol_value,
            "ai_mode": mode_terpilih,
            "user_memory": user_mem_value,
            "sync_telegram_response": sync_tele_value
        }
        save_config(cfg_data)
        
        # Terapkan mode AI ke core.py
        from core import set_mode_ai
        set_mode_ai(mode_terpilih)
        
        # Tampilkan indikator visual singkat
        if mode_terpilih == "local":
            mode_text = "LOKAL"
        elif mode_terpilih == "cloud_2_5":
            mode_text = "GEMINI 3.1 LITE"
        else:
            mode_text = "GEMINI 3.5"
            
        vn_app.label_saldo.config(text=f"Mode AI: {mode_text}")
        vn_app.root.after(2000, lambda: vn_app.label_saldo.config(text=f"Saldo: Rp {hitung_saldo():,}"))
        
        # Log
        vn_app.tambah_log(f"[SYSTEM]\nPengaturan disimpan. Text Speed: {vn_app.typing_speed}ms. Mode AI: {mode_text}. Memory updated.")
        
        # Feedback visual di dalam tab
        lbl_status.config(text="✓ Pengaturan & Memori berhasil disimpan!", fg="#00ff88")
        vn_app.root.after(2000, lambda: lbl_status.config(text="") if lbl_status.winfo_exists() else None)

    btn_save = tk.Button(scrollable_frame, text="Save & Apply Settings", font=("Consolas", 10, "bold"), 
                         bg="#222222", fg="white", activebackground="#333333", activeforeground="#00ffcc",
                         relief=tk.FLAT, command=simpan_setting_hybrid, padx=15, pady=8)
    btn_save.pack(anchor="w", padx=20, pady=10)
