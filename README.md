# 💻 Project Amadeus (Makise Kurisu AI Assistant)

Project Amadeus adalah asisten AI hybrid (otak lokal & cloud) yang dirancang menyerupai **Makise Kurisu** dari seri *Steins;Gate 0*. Sistem ini menggabungkan antarmuka bergaya *Visual Novel (VN)* dengan kemampuan mencatat keuangan otomatis berbasis kecerdasan buatan, sistem pengingat tugas (alarm) terintegrasi, pendeteksi emosi dinamis, transisi glitch visual, serta integrasi perpesanan dengan **Telegram Bot**.

---

## 🌟 Fitur Utama

- **🧠 Dual Brain (Hybrid Mode)**: 
  Dapat berpindah secara dinamis antara model AI lokal (**Ollama** dengan `llama3.1`) atau model cloud (**Google Gemini** dengan `gemini-2.5-flash` dan `gemini-3.5-flash`). Otak Gemini dilengkapi dengan **Automatic Failover** ke Ollama lokal secara otomatis jika terjadi limit kuota / koneksi terputus.
- **🎭 Visual Novel Interface**:
  Antarmuka berbasis GUI Tkinter yang kaya estetika cyberpunk dengan video latar belakang bergerak, efek glitch saat pergantian emosi karakter, dan suara pengisi suara Kurisu asli (voice barks) yang ter-cache dengan pengaturan volume custom.
- **💸 Financial Logger & Database**:
  Pencatat pengeluaran/pemasukan otomatis langsung dari percakapan (desktop & Telegram). Data disimpan secara teratur di database SQLite (`data/amadeus.db`).
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
- **🔒 Whitelist Security & Access Control**:
  Membatasi interaksi bot Telegram hanya untuk User ID yang terdaftar dalam whitelist `ALLOWED_TELEGRAM_USER_IDS` di file `.env` untuk keamanan data pribadi. Bot akan menampilkan User ID penolak secara otomatis jika ada percobaan akses tidak sah.
- **🎙️ Telegram Voice Note Reader**:
  Mengirimkan pesan suara (Voice Note) langsung ke bot Telegram. Bot akan mengunduh, mengonversi format audio menggunakan pustaka `soundfile` secara mandiri, mentranskripsinya otomatis ke teks (Bahasa Indonesia), dan memproses percakapan via AI.
- **🧹 Clean History Context**:
  Secara otomatis membersihkan blok kode JSON hasil ekstraksi AI (data keuangan, alarm, catatan, memori) sebelum disimpan ke dalam memori riwayat chat. Ini menghemat token API secara signifikan dan mencegah AI dari bias format atau halusinasi JSON.
- **💸 AI Financial Self-Correction (Edit & Hapus via Chat)**:
  Merevisi (mengedit) nominal/deskripsi atau membatalkan (menghapus) transaksi keuangan sebelumnya secara dinamis langsung lewat percakapan alami atau rekaman suara (berlaku di Desktop VN maupun bot Telegram). Saldo HUD dan grafik desktop otomatis ter-refresh secara instan.

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
pip install google-genai ollama pillow opencv-python pygame SpeechRecognition pyaudio python-telegram-bot matplotlib pystray soundfile
```

### 3. Konfigurasi API Key & Environment
Amadeus menyimpan file kredensial secara aman di folder terabaikan. Buat file `.env` di dalam folder root proyek atau di dalam folder `Ignore folder/`:

**File Path:** `Ignore folder/.env` atau `.env`
```env
GEMINI_API_KEY=isi_api_key_gemini_kamu_di_sini
TELEGRAM_BOT_TOKEN=isi_token_bot_telegram_kamu_di_sini
ALLOWED_TELEGRAM_USER_IDS=isi_user_id_telegram_kamu_di_sini (pisahkan dengan koma jika lebih dari satu)
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
* `/help` — Menampilkan panduan lengkap perintah bot dan panduan sinkronisasi obrolan AI.
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
├── data/                           # Folder data lokal aktif (diabaikan Git)
│   ├── amadeus.db                  # Database SQLite transaksi, pengingat tugas, & catatan
│   └── amadeus_config.json         # Pengaturan konfigurasi hybrid yang tersimpan
│
├── backups/                        # Arsip database lama / cadangan (diabaikan Git)
│   ├── amadeus_finansial.db        # Database lama pra-migrasi
│   └── amadeus_finansial.db.bak    # File cadangan database lama (.bak)
│
├── dump req/                       # Aset multimedia GUI
│   ├── amadeus_sprite/             # Sprite Amadeus untuk emosi aktif
│   ├── intro_bg/                   # Video latar belakang, video intro, & musik intro
│   └── logos/                      # Gambar ikon, logo, & tombol UI
│
├── src/                            # Kode sumber utama aplikasi
│   ├── ui/                         # Modul antarmuka GUI
│   │   └── tabs/                   # Komponen tab-tab overlay modular
│   │       ├── dashboard.py        # Visualisasi grafik & tabel transaksi keuangan
│   │       ├── logs.py             # System & conversation logs viewer
│   │       ├── notes.py            # Pencatatan harian & pratinjau detail
│   │       ├── reminders.py        # Form input alarm & list tugas
│   │       └── settings.py         # Slider typing speed, volume, mode AI, & memori
│   ├── core.py                     # Logika utama AI (Ollama/Gemini), SQLite & ingatan
│   ├── overlay.py                  # Entrypoint utama VN GUI (Tkinter) & background loops
│   ├── telegram_bot.py             # Bot Telegram asinkron asisten jarak jauh
│   └── terminal.py                 # Versi CLI terminal asisten Amadeus
│
├── support/                        # File utilitas, diagnostik, & skrip pengujian
│   ├── cek_model.py                # Pencarian model Gemini aktif pendukung API key
│   ├── test_limit_API.py           # Uji coba batasan/rate-limit API kuota Gemini
│   └── scratch_test_gemini.py      # Skrip coba-coba/test model Gemini & Ollama
│
├── run_amadeus.vbs                 # VBScript untuk startup Windows silent mode
└── README.md                       # Panduan informasi proyek
```

---

## 🤝 Kontribusi
Ingin mengembangkan Amadeus lebih jauh? Jangan ragu untuk melakukan fork dan mengirimkan *Pull Request*. 

