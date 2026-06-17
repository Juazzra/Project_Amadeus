import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox
import core
import os

def render_tab_log(vn_app):
    # Configure styles untuk ttk Notebook agar bernuansa dark/cyberpunk
    style = ttk.Style()
    style.configure("Custom.TNotebook", background="#1a1a1a", borderwidth=0)
    style.configure("Custom.TNotebook.Tab", background="#2a2a2a", foreground="white", font=("Consolas", 10), padding=[12, 5])
    style.map("Custom.TNotebook.Tab", 
              background=[("selected", "#1a1a1a"), ("active", "#333333")], 
              foreground=[("selected", "#00ffcc")])

    # Notebook Kontainer
    notebook = ttk.Notebook(vn_app.content_frame, style="Custom.TNotebook")
    notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

    tab_terminal = tk.Frame(notebook, bg="#1a1a1a")
    tab_lora = tk.Frame(notebook, bg="#1a1a1a")

    notebook.add(tab_terminal, text="📜 Terminal Logs")
    notebook.add(tab_lora, text="🧪 LoRA Dataset Manager")

    # =========================================================================
    # TAB 1: TERMINAL LOGS
    # =========================================================================
    lbl_title = tk.Label(tab_terminal, text="System & Conversation Logs", 
                         font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="white")
    lbl_title.pack(anchor="w", padx=10, pady=(10, 5))

    # Area ScrolledText
    log_area = scrolledtext.ScrolledText(tab_terminal, bg="#111111", fg="#e0e0e0", 
                                         font=("Consolas", 9), wrap=tk.WORD, bd=0, highlightthickness=0)
    log_area.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
    
    # Simpan referensi ke vn_app agar bisa di-update real-time
    vn_app.log_area = log_area
    
    # Masukkan log history
    for baris in vn_app.log_history:
        log_area.insert(tk.END, baris + "\n\n")
    log_area.config(state=tk.DISABLED)
    log_area.see(tk.END)

    # Control Frame
    control_frame = tk.Frame(tab_terminal, bg="#1a1a1a")
    control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

    # Tombol Bersihkan Log
    def bersihkan_log():
        vn_app.log_history.clear()
        log_area.config(state=tk.NORMAL)
        log_area.delete("1.0", tk.END)
        log_area.config(state=tk.DISABLED)
        print("[SYSTEM LOG] Log obrolan dibersihkan.")

    btn_clear = tk.Button(control_frame, text="Clear Log History", font=("Consolas", 9, "bold"),
                          bg="#333333", fg="white", activebackground="#555555", activeforeground="white",
                          relief=tk.FLAT, command=bersihkan_log, padx=10, pady=5)
    btn_clear.pack(side=tk.RIGHT)


    # =========================================================================
    # TAB 2: LORA DATASET MANAGER
    # =========================================================================
    lbl_lora_title = tk.Label(tab_lora, text="LoRA Training Dataset Scraper & Reviewer", 
                              font=("Consolas", 11, "bold"), bg="#1a1a1a", fg="#00ffcc")
    lbl_lora_title.pack(anchor="w", padx=10, pady=(10, 5))

    # Container Frame
    list_container = tk.Frame(tab_lora, bg="#1a1a1a")
    list_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # Scrollable Canvas
    canvas = tk.Canvas(list_container, bg="#111111", highlightthickness=0)
    scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=canvas.yview)
    scrollable_frame = tk.Frame(canvas, bg="#111111")

    scrollable_frame.bind(
        "<Configure>",
        lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
    )

    canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
    canvas.configure(yscrollcommand=scrollbar.set)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
    canvas.bind_all("<MouseWheel>", _on_mousewheel)
    
    def _bind_mw(event):
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
    def _unbind_mw(event):
        canvas.unbind_all("<MouseWheel>")
        
    canvas.bind("<Enter>", _bind_mw)
    canvas.bind("<Leave>", _unbind_mw)

    canvas.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Helper function untuk set rating
    def set_rating(row_id, new_rating, btn_dict):
        success = core.update_rating_dataset(row_id, new_rating)
        if success:
            color_map = {
                "gold": "#ffaa00",
                "good": "#22aa22",
                "neutral": "#555555",
                "bad": "#aa2222"
            }
            # Reset all button colors to default gray
            for r, btn in btn_dict.items():
                btn.config(bg="#333333")
            # Highlight selected
            btn_dict[new_rating].config(bg=color_map.get(new_rating, "#333333"))

    # Render rows from SQLite
    rows = core.ambil_dataset_lora(100)
    
    if not rows:
        lbl_empty = tk.Label(scrollable_frame, text="Belum ada riwayat obrolan terekam.", 
                             font=("Consolas", 10, "italic"), bg="#111111", fg="gray")
        lbl_empty.pack(padx=20, pady=20)
    else:
        for r_id, prompt, response, mood, context, model, rating, tanggal, sumber in rows:
            # Card Container
            card = tk.Frame(scrollable_frame, bg="#1d1d1d", bd=1, relief=tk.SOLID, padx=10, pady=10)
            card.pack(fill=tk.X, expand=True, padx=5, pady=5)

            # Metadata Info
            lbl_meta = tk.Label(card, text=f"📅 {tanggal} | 🧠 {model} | Sumber: {sumber.capitalize()}", 
                                font=("Consolas", 8), bg="#1d1d1d", fg="gray")
            lbl_meta.pack(anchor="w")

            # Prompt
            lbl_p_title = tk.Label(card, text="[User]:", font=("Consolas", 9, "bold"), bg="#1d1d1d", fg="#00ffcc")
            lbl_p_title.pack(anchor="w", pady=(5, 0))
            lbl_p_text = tk.Label(card, text=prompt, font=("Consolas", 9), bg="#1d1d1d", fg="white", 
                                  justify=tk.LEFT, wraplength=720, anchor="w")
            lbl_p_text.pack(anchor="w", padx=10)

            # Response
            lbl_r_title = tk.Label(card, text="[Amadeus]:", font=("Consolas", 9, "bold"), bg="#1d1d1d", fg="#ff77aa")
            lbl_r_title.pack(anchor="w", pady=(5, 0))
            lbl_r_text = tk.Label(card, text=response, font=("Consolas", 9), bg="#1d1d1d", fg="white", 
                                  justify=tk.LEFT, wraplength=720, anchor="w")
            lbl_r_text.pack(anchor="w", padx=10)

            # Context & Mood info if present
            extra_lines = []
            if mood and mood != "normal":
                extra_lines.append(f"Mood: {mood}")
            if context and context != "None":
                extra_lines.append(f"Konteks RAG: {context}")
            if extra_lines:
                lbl_extra = tk.Label(card, text=" | ".join(extra_lines), font=("Consolas", 8, "italic"), bg="#1d1d1d", fg="#aaaaaa", justify=tk.LEFT, wraplength=720, anchor="w")
                lbl_extra.pack(anchor="w", pady=(5, 0), padx=10)

            # Rating Buttons Frame
            rate_frame = tk.Frame(card, bg="#1d1d1d")
            rate_frame.pack(anchor="e", pady=(5, 0))

            btn_dict = {}
            color_map = {
                "gold": "#ffaa00",
                "good": "#22aa22",
                "neutral": "#555555",
                "bad": "#aa2222"
            }

            # ⭐ Emas Button
            btn_gold = tk.Button(rate_frame, text="⭐ Emas", font=("Consolas", 8, "bold"), fg="white", relief=tk.FLAT, padx=6, pady=2)
            btn_gold.config(command=lambda rid=r_id, rtype="gold", bdict=btn_dict: set_rating(rid, rtype, bdict))
            btn_gold.pack(side=tk.LEFT, padx=3)
            btn_dict["gold"] = btn_gold

            # 👍 Kurisu Button
            btn_good = tk.Button(rate_frame, text="👍 Kurisu", font=("Consolas", 8, "bold"), fg="white", relief=tk.FLAT, padx=6, pady=2)
            btn_good.config(command=lambda rid=r_id, rtype="good", bdict=btn_dict: set_rating(rid, rtype, bdict))
            btn_good.pack(side=tk.LEFT, padx=3)
            btn_dict["good"] = btn_good

            # 😐 Biasa Button
            btn_neutral = tk.Button(rate_frame, text="😐 Biasa", font=("Consolas", 8, "bold"), fg="white", relief=tk.FLAT, padx=6, pady=2)
            btn_neutral.config(command=lambda rid=r_id, rtype="neutral", bdict=btn_dict: set_rating(rid, rtype, bdict))
            btn_neutral.pack(side=tk.LEFT, padx=3)
            btn_dict["neutral"] = btn_neutral

            # 👎 OOC Button
            btn_bad = tk.Button(rate_frame, text="👎 OOC", font=("Consolas", 8, "bold"), fg="white", relief=tk.FLAT, padx=6, pady=2)
            btn_bad.config(command=lambda rid=r_id, rtype="bad", bdict=btn_dict: set_rating(rid, rtype, bdict))
            btn_bad.pack(side=tk.LEFT, padx=3)
            btn_dict["bad"] = btn_bad

            # Initialize colors based on current rating
            for rtype, btn in btn_dict.items():
                if rtype == rating:
                    btn.config(bg=color_map[rtype])
                else:
                    btn.config(bg="#333333")

    # Ekspor dataset control
    export_frame = tk.Frame(tab_lora, bg="#1a1a1a")
    export_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=10, pady=10)

    def lakukan_ekspor():
        success, msg = core.ekspor_dataset_lora_jsonl()
        if success:
            messagebox.showinfo("Ekspor Berhasil", msg)
        else:
            messagebox.showerror("Ekspor Gagal", f"Error: {msg}")

    btn_export = tk.Button(export_frame, text="📥 Export Dataset (JSONL)", font=("Consolas", 10, "bold"),
                           bg="#00ffcc", fg="black", activebackground="#00cc99", activeforeground="black",
                           relief=tk.FLAT, command=lakukan_ekspor, padx=15, pady=6)
    btn_export.pack(side=tk.LEFT)
