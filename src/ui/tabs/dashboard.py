import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import csv
import os
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from datetime import datetime
import core
from core import ambil_riwayat_transaksi, hitung_saldo, hapus_transaksi

def render_tab_visualisasi(vn_app):
    # Split pane kiri (Visualisasi/Grafik) dan kanan (Tabel/Riwayat & Aksi)
    main_frame = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
    
    left_frame = tk.Frame(main_frame, bg="#1a1a1a", width=380)
    left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
    left_frame.pack_propagate(False)
    
    right_frame = tk.Frame(main_frame, bg="#1a1a1a", width=390)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
    right_frame.pack_propagate(False)

    # --- SEKTOR KIRI: GRAFIK MATPLOTLIB ---
    records = ambil_riwayat_transaksi()
    if not records:
        lbl_empty = tk.Label(left_frame, text="Belum ada data transaksi\nuntuk visualisasi.", 
                             font=("Consolas", 10, "italic"), bg="#1a1a1a", fg="gray")
        lbl_empty.pack(expand=True)
    else:
        # 1. Olah data kategori pengeluaran (Pie Chart)
        kategori_pengeluaran = {}
        for _, _, jns, nom, kat, _ in records:
            if jns.lower() == 'pengeluaran':
                kategori_pengeluaran[kat] = kategori_pengeluaran.get(kat, 0) + nom

        # 2. Olah data tren saldo (Line Chart)
        chronological_records = sorted(records, key=lambda x: x[1])
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
                tgl_fmt = dt.strftime('%m-%d')
            except:
                tgl_fmt = tgl[5:10]
                
            dates.append(tgl_fmt)
            balances.append(current_balance)

        # Membuat Figure Matplotlib bertema gelap, stacked secara vertikal
        fig = plt.Figure(figsize=(3.6, 4.0), facecolor='#1a1a1a')
        
        # Subplot 1: Pie Chart Pengeluaran (Top)
        ax1 = fig.add_subplot(211)
        if kategori_pengeluaran:
            labels = list(kategori_pengeluaran.keys())
            sizes = list(kategori_pengeluaran.values())
            colors = ['#00ffcc', '#ff3366', '#33ccff', '#ffcc00', '#9933ff', '#ff9900']
            
            wedges, texts, autotexts = ax1.pie(
                sizes, labels=labels, autopct='%1.0f%%', startangle=90, 
                colors=colors[:len(labels)], textprops=dict(color="w", fontsize=7)
            )
            for text in texts:
                text.set_color("w")
                text.set_fontname("Consolas")
            for autotext in autotexts:
                autotext.set_fontsize(7)
                autotext.set_weight('bold')
                autotext.set_fontname("Consolas")
                
            ax1.set_title("Kategori Pengeluaran", color='white', fontname='Consolas', fontsize=9, fontweight='bold', pad=2)
        else:
            ax1.text(0.5, 0.5, "Tidak ada data\npengeluaran", color='gray', ha='center', va='center', fontname='Consolas', fontsize=9)
            ax1.axis('off')
            
        # Subplot 2: Line Chart Tren Saldo (Bottom)
        ax2 = fig.add_subplot(212)
        if dates:
            ax2.plot(dates, balances, color='#00ffcc', marker='o', markersize=2, linewidth=1.0, label='Saldo')
            ax2.fill_between(dates, balances, color='#00ffcc', alpha=0.1)
            ax2.set_title("Tren Saldo Kumulatif", color='white', fontname='Consolas', fontsize=9, fontweight='bold', pad=2)
            ax2.set_facecolor('#111111')
            ax2.tick_params(colors='white', labelsize=7)
            ax2.grid(True, color='#333333', linestyle='--', linewidth=0.5)
            
            for tick in ax2.get_xticklabels():
                tick.set_rotation(25)
                tick.set_fontname('Consolas')
            for tick in ax2.get_yticklabels():
                tick.set_fontname('Consolas')
                
            ax2.xaxis.set_major_locator(ticker.MaxNLocator(4))
            ax2.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, pos: f'Rp {int(x):,}'))
        else:
            ax2.text(0.5, 0.5, "Tidak ada data\ntransaksi", color='gray', ha='center', va='center', fontname='Consolas', fontsize=9)
            ax2.axis('off')
            
        fig.tight_layout()
        
        # Embed Figure ke widget Tkinter
        canvas = FigureCanvasTkAgg(fig, master=left_frame)
        canvas.draw()
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(fill=tk.BOTH, expand=True)
        canvas_widget.config(bg="#1a1a1a")

    # --- SEKTOR KANAN: TABEL RIWAYAT TRANSAKSI ---
    # Configure styles untuk Treeview agar bernuansa dark/cyberpunk
    style = ttk.Style()
    style.theme_use("clam")
    style.configure("Custom.Treeview", 
                    background="#1a1a1a", 
                    foreground="white", 
                    fieldbackground="#1a1a1a", 
                    rowheight=22,
                    font=("Consolas", 8))
    style.map("Custom.Treeview", 
              background=[("selected", "#333333")], 
              foreground=[("selected", "#00ffcc")])
    style.configure("Custom.Treeview.Heading", 
                    background="#2a2a2a", 
                    foreground="white", 
                    font=("Consolas", 8, "bold"),
                    borderwidth=0)

    lbl_table_title = tk.Label(right_frame, text="Daftar Transaksi Keuangan", font=("Consolas", 9, "bold"), bg="#1a1a1a", fg="white")
    lbl_table_title.pack(anchor="w", pady=(0, 2))

    # Container Frame untuk Treeview dan Scrollbar
    tree_frame = tk.Frame(right_frame, bg="#1a1a1a")
    tree_frame.pack(fill=tk.BOTH, expand=True, pady=2)

    # Setup columns
    cols = ("ID", "Waktu", "Jenis", "Nominal", "Kategori", "Deskripsi")
    vn_app.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", style="Custom.Treeview")
    
    # Scrollbar
    scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=vn_app.tree.yview)
    vn_app.tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)
    vn_app.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # Set Column Headings & Widths
    vn_app.tree.heading("ID", text="ID")
    vn_app.tree.heading("Waktu", text="Waktu")
    vn_app.tree.heading("Jenis", text="Jenis")
    vn_app.tree.heading("Nominal", text="Nominal")
    vn_app.tree.heading("Kategori", text="Kat")
    vn_app.tree.heading("Deskripsi", text="Deskripsi")

    vn_app.tree.column("ID", width=30, minwidth=20, anchor=tk.CENTER)
    vn_app.tree.column("Waktu", width=90, minwidth=80, anchor=tk.CENTER)
    vn_app.tree.column("Jenis", width=60, minwidth=50, anchor=tk.CENTER)
    vn_app.tree.column("Nominal", width=80, minwidth=70, anchor=tk.E)
    vn_app.tree.column("Kategori", width=65, minwidth=50, anchor=tk.W)
    vn_app.tree.column("Deskripsi", width=120, minwidth=80, anchor=tk.W)

    # Tags untuk mewarnai baris pemasukan/pengeluaran
    vn_app.tree.tag_configure("pemasukan", foreground="#00ff88")
    vn_app.tree.tag_configure("pengeluaran", foreground="#ff4444")

    # Fungsi memuat data ke Treeview
    def isi_tabel():
        for item in vn_app.tree.get_children():
            vn_app.tree.delete(item)
        
        records_data = ambil_riwayat_transaksi()
        for r_id, tgl, jns, nom, kat, dsk in records_data:
            tag = "pemasukan" if jns.lower() == "pemasukan" else "pengeluaran"
            nominal_fmt = f"Rp {nom:,}"
            vn_app.tree.insert("", tk.END, values=(r_id, tgl[5:16], jns.upper(), nominal_fmt, kat, dsk), tags=(tag,))
    
    isi_tabel()

    # Bottom Bar untuk Aksi
    control_frame = tk.Frame(right_frame, bg="#1a1a1a")
    control_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))

    # Tombol Analisis AI
    btn_analisis = tk.Button(control_frame, text="📊 Analisis AI", font=("Consolas", 8, "bold"),
                             bg="#115e59", fg="white", activebackground="#14b8a6", activeforeground="white",
                             relief=tk.FLAT, command=vn_app.minta_analisis_pengeluaran, padx=5, pady=3)
    btn_analisis.pack(side=tk.RIGHT, padx=2)

    # Tombol Export CSV
    btn_export = tk.Button(control_frame, text="Export CSV", font=("Consolas", 8, "bold"),
                           bg="#1e293b", fg="white", activebackground="#334155", activeforeground="white",
                           relief=tk.FLAT, command=vn_app.ekspor_riwayat_csv, padx=5, pady=3)
    btn_export.pack(side=tk.RIGHT, padx=2)

    # Tombol Hapus Terpilih
    def proses_hapus():
        selected = vn_app.tree.selection()
        if not selected:
            return
        
        item_values = vn_app.tree.item(selected[0], "values")
        t_id = item_values[0]
        
        if hapus_transaksi(t_id):
            print(f"[SYSTEM LOG] Transaksi ID {t_id} berhasil dihapus.")
            vn_app.log_history.append(f"[SYSTEM]\nTransaksi ID {t_id} dihapus. Saldo diperbarui.")
            
            # Re-render the visualisasi tab to reflect updated charts and list
            vn_app.render_tab_visualisasi()
            
            # Update saldo HUD di main UI
            saldo_baru = hitung_saldo()
            vn_app.label_saldo.config(text=f"Saldo: Rp {saldo_baru:,}")
            
    btn_hapus = tk.Button(control_frame, text="Hapus", font=("Consolas", 8, "bold"),
                          bg="#501010", fg="white", activebackground="#aa2222", activeforeground="white",
                          relief=tk.FLAT, command=proses_hapus, padx=5, pady=3)
    btn_hapus.pack(side=tk.RIGHT, padx=2)

    # Tombol Hapus Semua
    btn_hapus_semua = tk.Button(control_frame, text="Hapus Semua", font=("Consolas", 8, "bold"),
                                bg="#7f1d1d", fg="white", activebackground="#b91c1c", activeforeground="white",
                                relief=tk.FLAT, command=vn_app.hapus_seluruh_riwayat, padx=5, pady=3)
    btn_hapus_semua.pack(side=tk.LEFT, padx=2)
