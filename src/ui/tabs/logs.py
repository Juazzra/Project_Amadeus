import tkinter as tk
from tkinter import scrolledtext

def render_tab_log(vn_app):
    # Judul Tab
    lbl_title = tk.Label(vn_app.content_frame, text="System & Conversation Logs", 
                         font=("Consolas", 12, "bold"), bg="#1a1a1a", fg="white")
    lbl_title.pack(anchor="w", padx=15, pady=(15, 5))

    # Area ScrolledText
    log_area = scrolledtext.ScrolledText(vn_app.content_frame, bg="#111111", fg="#e0e0e0", 
                                         font=("Consolas", 10), wrap=tk.WORD, bd=0, highlightthickness=0)
    log_area.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
    
    # Masukkan log history
    for baris in vn_app.log_history:
        log_area.insert(tk.END, baris + "\n\n")
    log_area.config(state=tk.DISABLED)
    log_area.see(tk.END)

    # Control Frame
    control_frame = tk.Frame(vn_app.content_frame, bg="#1a1a1a")
    control_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=15, pady=15)

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
