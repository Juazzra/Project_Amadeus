import tkinter as tk
from tkinter import ttk, scrolledtext
import core

def render_tab_catatan(vn_app):
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
    main_frame = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)

    # --- SEKTOR KIRI: FORM INPUT ---
    left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=250)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
    left_frame.pack_propagate(False)

    lbl_form_title = tk.Label(left_frame, text="Buat Catatan Baru", font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="#00ffcc")
    lbl_form_title.pack(anchor="w", pady=(0, 10))

    lbl_judul = tk.Label(left_frame, text="Judul Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
    lbl_judul.pack(anchor="w", pady=(5, 2))

    vn_app.entry_note_judul = tk.Entry(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 10), insertbackground="white", relief=tk.FLAT)
    vn_app.entry_note_judul.pack(fill=tk.X, pady=(0, 10))

    lbl_konten = tk.Label(left_frame, text="Isi Catatan:", font=("Consolas", 9), bg="#1a1a1a", fg="#e0e0e0")
    lbl_konten.pack(anchor="w", pady=(5, 2))

    # Text area untuk multi-line note content
    vn_app.txt_note_konten = tk.Text(left_frame, bg="#2a2a2a", fg="white", font=("Consolas", 9), insertbackground="white", height=10, relief=tk.FLAT)
    vn_app.txt_note_konten.pack(fill=tk.BOTH, expand=True, pady=(0, 15))

    lbl_error_note = tk.Label(left_frame, text="", font=("Consolas", 8), bg="#1a1a1a", fg="#ff4444", wraplength=230, justify=tk.LEFT)
    lbl_error_note.pack(fill=tk.X, pady=5)

    def simpan_catatan_baru():
        judul_val = vn_app.entry_note_judul.get().strip()
        konten_val = vn_app.txt_note_konten.get("1.0", tk.END).strip()
        
        if not konten_val:
            lbl_error_note.config(text="* Isi catatan tidak boleh kosong!", fg="#ff4444")
            return
            
        if not judul_val:
            # Judul otomatis dari baris pertama
            words = konten_val.split()
            judul_val = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
            
        if core.tambah_catatan(judul_val, konten_val, "desktop"):
            vn_app.log_history.append(f"[SYSTEM]\nCatatan disimpan: '{judul_val}'.")
            vn_app.render_tab_catatan() # Re-render to update
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
    vn_app.tree_notes = ttk.Treeview(top_right, columns=cols, show="headings", style="Custom.Treeview")
    
    scroll = ttk.Scrollbar(top_right, orient="vertical", command=vn_app.tree_notes.yview)
    vn_app.tree_notes.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    vn_app.tree_notes.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    vn_app.tree_notes.heading("ID", text="ID")
    vn_app.tree_notes.heading("Tanggal", text="Tanggal")
    vn_app.tree_notes.heading("Judul", text="Judul Catatan")
    vn_app.tree_notes.heading("Sumber", text="Sumber")

    vn_app.tree_notes.column("ID", width=40, minwidth=30, anchor=tk.CENTER)
    vn_app.tree_notes.column("Tanggal", width=130, minwidth=110, anchor=tk.CENTER)
    vn_app.tree_notes.column("Judul", width=200, minwidth=150, anchor=tk.W)
    vn_app.tree_notes.column("Sumber", width=70, minwidth=60, anchor=tk.CENTER)

    # Load data to table
    catatan_list = core.ambil_semua_catatan()
    for c_id, tgl, judul, konten, sumber in catatan_list:
        vn_app.tree_notes.insert("", tk.END, values=(c_id, tgl, judul, sumber.upper()))

    # Sektor kanan bawah (Detail Catatan)
    bottom_right = tk.Frame(right_frame, bg="#1a1a1a")
    bottom_right.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True, pady=(10, 0))

    lbl_preview_title = tk.Label(bottom_right, text="Isi Catatan Detail", font=("Consolas", 10, "bold"), bg="#1a1a1a", fg="#00ffcc")
    lbl_preview_title.pack(anchor="w", pady=(0, 5))

    # Text area pratinjau yang read-only
    vn_app.txt_note_preview = scrolledtext.ScrolledText(bottom_right, bg="#111111", fg="#e0e0e0", font=("Consolas", 10), wrap=tk.WORD, bd=0, highlightthickness=0, height=8)
    vn_app.txt_note_preview.pack(fill=tk.BOTH, expand=True)
    vn_app.txt_note_preview.config(state=tk.DISABLED)

    # Fungsi pengisian detail otomatis saat baris tabel diklik
    def tampilkan_detail_catatan(event):
        selected = vn_app.tree_notes.selection()
        if not selected: return
        item_values = vn_app.tree_notes.item(selected[0], "values")
        c_id = int(item_values[0])
        
        # Cari isi konten catatan dari data
        target_catatan = next((c for c in catatan_list if c[0] == c_id), None)
        if target_catatan:
            _, _, _, konten, _ = target_catatan
            vn_app.txt_note_preview.config(state=tk.NORMAL)
            vn_app.txt_note_preview.delete("1.0", tk.END)
            vn_app.txt_note_preview.insert(tk.END, konten)
            vn_app.txt_note_preview.config(state=tk.DISABLED)

    vn_app.tree_notes.bind("<<TreeviewSelect>>", tampilkan_detail_catatan)

    # Action Buttons di bawah detail area
    action_frame = tk.Frame(bottom_right, bg="#1a1a1a")
    action_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

    def hapus_catatan_terpilih():
        selected = vn_app.tree_notes.selection()
        if not selected: return
        item_values = vn_app.tree_notes.item(selected[0], "values")
        c_id = int(item_values[0])
        if core.hapus_catatan(c_id):
            vn_app.log_history.append(f"[SYSTEM]\nCatatan ID {c_id} dihapus.")
            vn_app.render_tab_catatan()

    btn_hapus_note = tk.Button(action_frame, text="Hapus Catatan Terpilih", font=("Consolas", 9, "bold"),
                               bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                               relief=tk.FLAT, command=hapus_catatan_terpilih, padx=10, pady=5)
    btn_hapus_note.pack(side=tk.RIGHT)
