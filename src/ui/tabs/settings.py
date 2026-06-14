import tkinter as tk
import core
from core import load_config, save_config, hitung_saldo

def render_tab_settings(vn_app):
    # Judul Tab
    lbl_title = tk.Label(vn_app.content_frame, text="Amadeus Settings & Configuration", 
                         font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
    lbl_title.pack(anchor="w", padx=15, pady=(10, 10))

    # --- SEKTOR 1: KECEPATAN TEKS ---
    lbl_speed = tk.Label(vn_app.content_frame, text="Text Typing Speed (ms/character):", 
                         font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_speed.pack(anchor="w", padx=20)
    
    speed_slider = tk.Scale(vn_app.content_frame, from_=10, to=150, orient=tk.HORIZONTAL, 
                            bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                            activebackground="#00ffcc")
    speed_slider.set(vn_app.typing_speed)
    speed_slider.pack(anchor="w", padx=20, pady=(0, 10))

    # --- SEKTOR 1B: VOLUME SUARA ---
    lbl_volume = tk.Label(vn_app.content_frame, text="Volume Suara Kurisu & Musik (%):", 
                          font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_volume.pack(anchor="w", padx=20, pady=(5, 0))
    
    volume_slider = tk.Scale(vn_app.content_frame, from_=0, to=100, orient=tk.HORIZONTAL, 
                             bg="#1a1a1a", fg="white", highlightthickness=0, length=300,
                             activebackground="#00ffcc")
    volume_slider.set(int(vn_app.voice_volume * 100))
    volume_slider.pack(anchor="w", padx=20, pady=(0, 10))

    # --- SEKTOR 2: PEMILIHAN OTAK AI ---
    lbl_brain = tk.Label(vn_app.content_frame, text="AI Brain Source (Mode AI):", 
                         font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_brain.pack(anchor="w", padx=20)
    
    core_mode = core.MODE_AI_AKTIF
    if core_mode == "cloud":
        core_mode = "cloud_2_5"
    vn_app.var_ai_mode = tk.StringVar(value=core_mode)
    
    frame_radio = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    frame_radio.pack(anchor="w", padx=20, pady=5)

    r_local = tk.Radiobutton(frame_radio, text="Lokal (Ollama)", variable=vn_app.var_ai_mode, value="local", 
                            bg="#1a1a1a", fg="#00ffcc", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                            activeforeground="#00ffcc", font=("Consolas", 10))
    r_local.pack(side=tk.LEFT, padx=(0, 15))
    
    r_cloud_2_5 = tk.Radiobutton(frame_radio, text="Gemini 2.5", variable=vn_app.var_ai_mode, value="cloud_2_5", 
                                bg="#1a1a1a", fg="#ffcc00", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                activeforeground="#ffcc00", font=("Consolas", 10))
    r_cloud_2_5.pack(side=tk.LEFT, padx=(0, 15))

    r_cloud_3_5 = tk.Radiobutton(frame_radio, text="Gemini 3.5", variable=vn_app.var_ai_mode, value="cloud_3_5", 
                                bg="#1a1a1a", fg="#e11d48", selectcolor="#2a2a2a", activebackground="#1a1a1a",
                                activeforeground="#e11d48", font=("Consolas", 10))
    r_cloud_3_5.pack(side=tk.LEFT)

    lbl_warning = tk.Label(vn_app.content_frame, text="*Mengubah mode otak akan mereset ingatan sesi aktif Amadeus.", 
                           font=("Consolas", 8, "italic"), bg="#1a1a1a", fg="gray")
    lbl_warning.pack(anchor="w", padx=20, pady=(0, 5))

    # --- SEKTOR 3: MEMORI USER (TENTANG SAYA) ---
    lbl_memory = tk.Label(vn_app.content_frame, text="User Memory (Informasi Tentang Saya):", 
                          font=("Consolas", 10), bg="#1a1a1a", fg="#e0e0e0")
    lbl_memory.pack(anchor="w", padx=20, pady=(5, 2))
    
    cfg = load_config()
    user_mem = cfg.get("user_memory", "")
    
    vn_app.txt_memory = tk.Text(vn_app.content_frame, bg="#111111", fg="white", 
                              font=("Consolas", 9), insertbackground="white", 
                              height=3, width=70, relief=tk.FLAT)
    vn_app.txt_memory.pack(anchor="w", padx=20, pady=(0, 5))
    vn_app.txt_memory.insert(tk.END, user_mem)

    # Label status keberhasilan
    lbl_status = tk.Label(vn_app.content_frame, text="", font=("Consolas", 10, "bold"), bg="#1a1a1a")
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
        import pygame
        pygame.mixer.music.set_volume(vn_app.voice_volume)
        for snd in vn_app.sound_cache.values():
            snd.set_volume(vn_app.voice_volume)
        
        # 4. Simpan mode AI
        mode_terpilih = vn_app.var_ai_mode.get()
        
        # 5. Tulis ke file amadeus_config.json
        cfg_data = {
            "typing_speed": vn_app.typing_speed,
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
            
        vn_app.label_saldo.config(text=f"Mode AI: {mode_text}")
        vn_app.root.after(2000, lambda: vn_app.label_saldo.config(text=f"Saldo: Rp {hitung_saldo():,}"))
        
        # Log
        vn_app.log_history.append(f"[SYSTEM]\nPengaturan disimpan. Text Speed: {vn_app.typing_speed}ms. Mode AI: {mode_text}. Memory updated.")
        
        # Feedback visual di dalam tab
        lbl_status.config(text="✓ Pengaturan & Memori berhasil disimpan!", fg="#00ff88")
        vn_app.root.after(2000, lambda: lbl_status.config(text="") if lbl_status.winfo_exists() else None)

    btn_save = tk.Button(vn_app.content_frame, text="Save & Apply Settings", font=("Consolas", 10, "bold"), 
                         bg="#222222", fg="white", activebackground="#333333", activeforeground="#00ffcc",
                         relief=tk.FLAT, command=simpan_setting_hybrid, padx=15, pady=8)
    btn_save.pack(anchor="w", padx=20, pady=10)
