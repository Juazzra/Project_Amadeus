import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta
import re
import core

def render_tab_tugas(vn_app):
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
    main_frame = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
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
    placeholder_waktu = (datetime.now() + timedelta(minutes=10)).strftime('%H:%M')
    vn_app.entry_tugas_waktu = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
    vn_app.entry_tugas_waktu.pack(fill=tk.X, pady=(0, 10))
    vn_app.entry_tugas_waktu.insert(0, placeholder_waktu)

    lbl_desc = tk.Label(left_frame, text="Deskripsi Tugas / Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
    lbl_desc.pack(anchor="w", pady=(5, 2))

    vn_app.entry_tugas_desc = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
    vn_app.entry_tugas_desc.pack(fill=tk.X, pady=(0, 15))

    lbl_error_tugas = tk.Label(left_frame, text="", font=("Consolas", 8), bg="#1a1a1a", fg="#ff4444", wraplength=230, justify=tk.LEFT)
    lbl_error_tugas.pack(fill=tk.X, pady=5)

    def simpan_tugas_baru():
        waktu_val = vn_app.entry_tugas_waktu.get().strip()
        desc_val = vn_app.entry_tugas_desc.get().strip()
        
        if not waktu_val or not desc_val:
            lbl_error_tugas.config(text="* Waktu dan deskripsi wajib diisi!", fg="#ff4444")
            return
            
        # Validasi format waktu
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
            
        if core.tambah_tugas(waktu_val, desc_val, "desktop"):
            vn_app.log_history.append(f"[SYSTEM]\nPengingat disimpan: '{desc_val}' pada {waktu_val}.")
            vn_app.render_tab_tugas() # Re-render tab to update list
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
    vn_app.tree_tugas = ttk.Treeview(right_frame, columns=cols, show="headings", style="Custom.Treeview")
    
    scroll = ttk.Scrollbar(right_frame, orient="vertical", command=vn_app.tree_tugas.yview)
    vn_app.tree_tugas.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    vn_app.tree_tugas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    vn_app.tree_tugas.heading("ID", text="ID")
    vn_app.tree_tugas.heading("Waktu", text="Waktu")
    vn_app.tree_tugas.heading("Deskripsi", text="Deskripsi")
    vn_app.tree_tugas.heading("Status", text="Status")
    vn_app.tree_tugas.heading("Sumber", text="Sumber")

    vn_app.tree_tugas.column("ID", width=40, minwidth=30, anchor=tk.CENTER)
    vn_app.tree_tugas.column("Waktu", width=120, minwidth=100, anchor=tk.CENTER)
    vn_app.tree_tugas.column("Deskripsi", width=180, minwidth=150, anchor=tk.W)
    vn_app.tree_tugas.column("Status", width=80, minwidth=60, anchor=tk.CENTER)
    vn_app.tree_tugas.column("Sumber", width=70, minwidth=60, anchor=tk.CENTER)

    vn_app.tree_tugas.tag_configure("aktif", foreground="#00ffcc")
    vn_app.tree_tugas.tag_configure("selesai", foreground="gray")
    vn_app.tree_tugas.tag_configure("lewat", foreground="#ff4444")

    # Load data to table
    tugas_list = core.ambil_semua_tugas()
    for t_id, waktu, desc, status, sumber in tugas_list:
        vn_app.tree_tugas.insert("", tk.END, values=(t_id, waktu, desc, status.upper(), sumber.upper()), tags=(status,))

    # Control Frame di bawah tabel
    control_frame = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=(0, 15))

    def selesaikan_tugas_terpilih():
        selected = vn_app.tree_tugas.selection()
        if not selected: return
        item_values = vn_app.tree_tugas.item(selected[0], "values")
        t_id = int(item_values[0])
        if core.update_status_tugas(t_id, 'selesai'):
            vn_app.log_history.append(f"[SYSTEM]\nPengingat ID {t_id} selesai.")
            vn_app.render_tab_tugas()

    def hapus_tugas_terpilih():
        selected = vn_app.tree_tugas.selection()
        if not selected: return
        item_values = vn_app.tree_tugas.item(selected[0], "values")
        t_id = int(item_values[0])
        if core.hapus_tugas(t_id):
            vn_app.log_history.append(f"[SYSTEM]\nPengingat ID {t_id} dihapus.")
            vn_app.render_tab_tugas()

    btn_selesai = tk.Button(control_frame, text="✓ Selesai", font=("Consolas", 9, "bold"),
                            bg="#1e293b", fg="white", activebackground="#334155", activeforeground="white",
                            relief=tk.FLAT, command=selesaikan_tugas_terpilih, padx=10, pady=5)
    btn_selesai.pack(side=tk.RIGHT, padx=5)

    btn_hapus = tk.Button(control_frame, text="Hapus", font=("Consolas", 9, "bold"),
                          bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                          relief=tk.FLAT, command=hapus_tugas_terpilih, padx=10, pady=5)
    btn_hapus.pack(side=tk.RIGHT, padx=5)
