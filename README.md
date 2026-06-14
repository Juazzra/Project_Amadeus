# 💻 Project Amadeus (Makise Kurisu AI Assistant)

Project Amadeus adalah asisten AI hybrid (otak lokal & cloud) yang dirancang menyerupai **Makise Kurisu** dari seri *Steins;Gate 0*. Sistem ini menggabungkan antarmuka bergaya *Visual Novel (VN)* dengan kemampuan mencatat keuangan otomatis berbasis kecerdasan buatan, sistem pengingat tugas (alarm) terintegrasi, pendeteksi emosi dinamis, transisi glitch visual, serta integrasi perpesanan dengan **Telegram Bot**.

---

## 🌟 Fitur Utama

- **🧠 Dual Brain (Hybrid Mode)**: 
  Dapat berpindah secara dinamis antara model AI lokal (**Ollama** dengan `llama3.1`) atau model cloud (**Google Gemini** dengan `gemini-2.5-flash` dan `gemini-3.5-flash`). Otak Gemini dilengkapi dengan **Automatic Failover** ke Ollama lokal secara otomatis jika terjadi limit kuota / koneksi terputus.
- **🎭 Visual Novel Interface**:
  Antarmuka berbasis GUI Tkinter yang kaya estetika cyberpunk dengan video latar belakang bergerak, efek glitch saat pergantian emosi karakter, dan suara pengisi suara Kurisu asli (voice barks) yang ter-cache dengan pengaturan volume custom.
- **💸 Financial Logger & Database**:
  Pencatat pengeluaran/pemasukan otomatis langsung dari percakapan (desktop & Telegram). Data disimpan secara teratur di database SQLite (`amadeus_finansial.db`).
- **📊 Unified Overlay Panel**:
  - **💸 Transaksi**: Tabel riwayat keuangan cyberpunk, hapus data, ekspor ke CSV, dan fitur **Analisis AI Finansial** yang memberikan kritik/saran keuangan dengan gaya khas *tsundere* Kurisu.
  - **📊 Visualisasi**: Grafik visual analisis pengeluaran (Pie Chart) dan tren saldo kumulatif (Line Chart) berbasis Matplotlib yang ter-render di dalam GUI.
  - **📜 System Log**: Log percakapan dan sistem yang terperinci.
  - **⚙️ Settings**: Pengaturan kecepatan mengetik, volume audio, pergantian model AI, serta kustomisasi **User Memory** agar Kurisu selalu mengingat panggilan sayang dan sifat Anda.
- **🎙️ Speech Recognition (Input Suara)**: 
  Interaksi bebas genggam dengan menekan tombol mikrofon untuk berbicara langsung dalam Bahasa Indonesia ke sistem desktop.
- **⏰ Task Reminder & Alarm System (Desktop + Telegram Alert)**:
  - Catat alarm pengingat tugas langsung lewat tab `⏰ Pengingat` di overlay desktop atau lewat perintah Telegram `/tugas`.
  - Ketika alarm berbunyi: GUI akan otomatis memulihkan diri (jika di-minimize), memicu glitch ke pose terkejut/berpikir, memainkan alarm suara, memunculkan dialog VN pengingat, dan mengirimkan pesan push notifikasi langsung ke Telegram ponselmu.
- **📥 Native System Tray & RAM Trimming (background execution)**:
  - Menutup `[X]` jendela akan menyembunyikan Amadeus ke system tray Windows. Saat berjalan di latar belakang, OpenCV video loop di-pause (0% CPU).
  - Menggunakan integrasi Windows Win32 API (`SetProcessWorkingSetSize`), memori fisik (RAM) Amadeus langsung dipangkas otomatis dari **~300 MB** turun ke hanya **10-35 MB** saat di-minimize!
- **📝 Notes (Catatan) System (Desktop + Telegram Sync)**:
  Buat, baca, dan hapus catatan secara sinkron melalui tab `📝 Catatan` di GUI desktop atau langsung lewat bot Telegram. Mendukung penulisan judul manual atau penentuan judul otomatis (diambil dari 4 kata pertama isi catatan).
- **🤖 Telegram Bot Integration**:
  Telegram Bot berjalan otomatis di background thread asinkron untuk mencatat keuangan, mengecek saldo, mengganti model AI, melihat memori, mengelola alarm, serta menulis/membaca catatan dari jarak jauh.

---

## 🛠️ Persyaratan Sistem

- **Python 3.10+** (Direkomendasikan Python 3.13)
- **Ollama** (Jika ingin menjalankan model AI Lokal)
- **Google Gemini API Key** (Jika ingin menggunakan model AI Cloud)
- **Telegram Bot Token** (Jika ingin mengaktifkan sinkronisasi asisten Telegram)
- **Virtual Environment** (`.venv`)

---

## 🚀 Panduan Instalasi & Setup

### 1. Kloning Repositori
```bash
git clone https://github.com/Juazzra/Project_Amadeus.git
cd Project_Amadeus
```

### 2. Setup Virtual Environment & Install Dependencies
Pastikan virtual environment telah diaktifkan:

```powershell
# Windows PowerShell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Instal pustaka Python yang diperlukan:
```bash
pip install -r requirements.txt
```
*Atau instal manual pustaka utama berikut:*
```bash
pip install google-genai ollama pillow opencv-python pygame SpeechRecognition pyaudio python-telegram-bot matplotlib pystray
```

### 3. Konfigurasi API Key & Environment
Amadeus menyimpan file kredensial secara aman di folder terabaikan. Buat file `.env` di dalam folder root proyek atau di dalam folder `Ignore folder/`:

**File Path:** `Ignore folder/.env` atau `.env`
```env
GEMINI_API_KEY=isi_api_key_gemini_kamu_di_sini
TELEGRAM_BOT_TOKEN=isi_token_bot_telegram_kamu_di_sini
```

---

## 🕹️ Cara Menjalankan

### Running Mode GUI (Visual Novel + Telegram Bot)
Jalankan file visual utama untuk masuk ke mode Visual Novel dengan intro Steins;Gate. **Bot Telegram akan berjalan secara otomatis di latar belakang thread:**
```bash
python overlay.py
```

### Running Secara Silent/Latar Belakang di Windows (Startup)
Kamu bisa menggunakan skrip VBScript yang disediakan untuk menjalankan aplikasi secara diam-diam tanpa jendela hitam Command Prompt bermunculan:
```bash
# Cukup double-click file ini atau masukkan ke Windows Startup folder
run_amadeus.vbs
```

### Running Mode Terminal (CLI)
Jalankan versi terminal ringan jika hanya ingin mengobrol lewat command-line:
```bash
python terminal.py
```

---

## 🤖 Daftar Perintah Telegram Bot

Hubungi bot Telegram-mu dan gunakan perintah-perintah berikut:
* `/start` — Menampilkan pesan sambutan dan ringkasan menu asisten.
* `/settings` — Melihat pengaturan aktif (mode AI, memori, typing speed).
* `/model` — Mengganti otak AI (Lokal, Gemini 2.5, Gemini 3.5) via tombol keyboard inline.
* `/saldo` — Mengecek sisa saldo keuangan saat ini di database SQLite.
* `/riwayat` — Menampilkan 5 daftar transaksi keuangan terbaru.
* `/memory <teks>` — Melihat atau memperbarui memori Kurisu tentang diri Anda.
* `/tugas` — Melihat daftar pengingat alarm aktif dan cara penggunaannya.
* `/tugas <waktu> <deskripsi>` — Menambahkan pengingat tugas (contoh: `/tugas 15:30 Rapat Laboratorium`).
* `/tugas_selesai <id>` — Menandai tugas tertentu telah diselesaikan.
* `/tugas_hapus <id>` — Menghapus tugas dari database.
* `/note` — Menampilkan daftar catatan aktif dan petunjuk penggunaan.
* `/note <judul> | <konten>` — Membuat catatan baru dengan judul dan isi tertentu.
* `/note <konten>` — Membuat catatan baru dengan judul otomatis (diambil dari 4 kata pertama konten).
* `/note_detail <id>` — Membaca isi lengkap dari catatan berdasarkan ID.
* `/note_hapus <id>` — Menghapus catatan dari database berdasarkan ID.

---

## 📁 Struktur Proyek

```text
Project_Amadeus/
│
├── Ignore folder/                  # Folder aset lokal (tidak dipantau Git)
│   ├── .env                        # Lokasi penyimpanan API Key Gemini & Bot Token
│   ├── sprites Amadeus/            # Ratusan sprite visual VN Kurisu
│   └── voice/                      # File audio suara Kurisu (.wav)
│
├── dump req/                       # Aset multimedia GUI
│   ├── amadeus_sprite/             # Sprite Amadeus untuk emosi aktif
│   ├── background.mp4              # Video latar belakang terminal
│   ├── intro.mp3 & intro.mp4       # Musik & video intro Amadeus
│   ├── bar-chart.png               # Ikon visualisasi grafik
│   └── *_logo.png                  # Gambar ikon/tombol UI
│
├── core.py                         # Logika utama AI, SQLite & manajemen memori
├── overlay.py                      # Frontend GUI Visual Novel berbasis Tkinter & scheduling
├── telegram_bot.py                 # Bot Telegram asinkron untuk asisten jarak jauh
├── terminal.py                     # Versi CLI terminal asisten Amadeus
├── run_amadeus.vbs                 # VBScript untuk startup Windows silent mode
├── amadeus_config.json             # Pengaturan tersimpan (kecepatan ketik, mode, memori, volume)
├── amadeus_finansial.db            # Database SQLite transaksi keuangan, tugas pengingat, & catatan
└── README.md                       # Panduan informasi proyek
```

---

## 🤝 Kontribusi
Ingin mengembangkan Amadeus lebih jauh? Jangan ragu untuk melakukan fork dan mengirimkan *Pull Request*. 

*El Psy Kongroo.*
