# 💻 Project Amadeus (Makise Kurisu AI Assistant)

Project Amadeus adalah asisten AI hybrid (otak lokal & cloud) yang dirancang menyerupai **Makise Kurisu** dari seri *Steins;Gate 0*. Sistem ini menggabungkan antarmuka bergaya *Visual Novel (VN)* dengan kemampuan mencatat keuangan otomatis berbasis kecerdasan buatan, pendeteksi emosi dinamis, transisi glitch visual, serta input berbasis suara.

---

## 🌟 Fitur Utama

- **🧠 Dual Brain (Hybrid Mode)**: 
  Dapat berpindah secara dinamis antara model AI lokal (**Ollama** dengan `llama3.1`) atau model cloud (**Google Gemini** dengan `gemini-2.5-flash` dan `gemini-3.5-flash`).
- **🎭 Visual Novel Interface**:
  Antarmuka berbasis GUI Tkinter yang kaya estetika dengan background video bergerak, efek glitch saat pergantian emosi karakter, dan suara pengisi suara Kurisu asli yang sesuai dengan suasana hati.
- **💸 Financial Logger & Database**:
  Pencatat pengeluaran/pemasukan otomatis langsung dari percakapan. Data disimpan secara teratur di database SQLite (`amadeus_finansial.db`).
- **📊 Unified Overlay Panel**:
  - **💸 Transaksi**: Tabel riwayat keuangan cyberpunk, hapus data, ekspor ke CSV, dan fitur **Analisis AI Finansial** yang memberikan saran keuangan dengan gaya khas *tsundere* Kurisu.
  - **📜 System Log**: Log percakapan dan sistem yang terperinci.
  - **⚙️ Settings**: Pengaturan kecepatan mengetik teks, pergantian model AI, serta kustomisasi **User Memory** agar Kurisu selalu mengingat panggilan sayang dan sifat Anda.
- **🎙️ Speech Recognition (Input Suara)**: 
  Interaksi bebas genggam dengan menekan tombol mikrofon untuk berbicara langsung dalam Bahasa Indonesia.
- **📟 Terminal Mode**: 
  Versi CLI/terminal ringan untuk interaksi cepat tanpa antarmuka grafis.

---

## 🛠️ Persyaratan Sistem

- **Python 3.10+** (Direkomendasikan Python 3.13)
- **Ollama** (Jika ingin menjalankan model AI Lokal)
- **Google Gemini API Key** (Jika ingin menggunakan model AI Cloud)
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
*Catatan: Jika file `requirements.txt` belum ada, instal pustaka utama berikut:*
```bash
pip install google-genai ollama pillow opencv-python pygame SpeechRecognition pyaudio
```

### 3. Konfigurasi API Key & Environment
Amadeus menyimpan file kredensial secara aman di folder terabaikan. Buat file `.env` di dalam folder `Ignore folder/`:

**File Path:** `Ignore folder/.env`
```env
GEMINI_API_KEY=isi_api_key_gemini_kamu_di_sini
```

---

## 🕹️ Cara Menjalankan

### Running Mode GUI (Visual Novel)
Jalankan file visual utama untuk masuk ke mode Visual Novel dengan intro Steins;Gate:
```bash
python overlay.py
```

### Running Mode Terminal (CLI)
Jalankan versi terminal ringan:
```bash
python terminal.py
```

### Diagnostik & Pengujian API
Jika Anda ingin mengetes daftar model yang tersedia untuk API Key Anda atau melakukan diagnostik pembatasan kuota (rate-limit), Anda bisa menjalankan skrip berikut:
```bash
# Cek model yang tersedia
python cek_model.py

# Tes performa model (Diagnostik Quota Limit 429)
python test_limit_API.py
```

---

## 📁 Struktur Proyek

```text
Project_Amadeus/
│
├── Ignore folder/                  # Folder aset lokal (tidak dipantau Git)
│   ├── .env                        # Lokasi penyimpanan API Key Gemini
│   ├── sprites Amadeus/            # Ratusan sprite visual VN Kurisu
│   └── voice/                      # File audio suara Kurisu (.wav)
│
├── dump req/                       # Aset multimedia GUI
│   ├── amadeus_sprite/             # Sprite Amadeus untuk emosi aktif
│   ├── background.mp4              # Video latar belakang terminal
│   ├── intro.mp3 & intro.mp4       # Musik & video intro Amadeus
│   └── *_logo.png                  # Gambar ikon/tombol UI
│
├── core.py                         # Logika utama AI, SQLite & manajemen memori
├── overlay.py                      # Frontend GUI Visual Novel berbasis Tkinter
├── terminal.py                     # Versi CLI terminal asisten Amadeus
├── amadeus_config.json             # Pengaturan tersimpan (kecepatan ketik, mode, memori user)
├── amadeus_finansial.db            # Database SQLite transaksi keuangan
└── README.md                       # Panduan informasi proyek
```

---

## 🚧 Roadmap (Planned Features)

- **📱 Bot Integration (Telegram/WhatsApp)**: Menyambungkan database SQLite dengan API perpesanan agar input *income/outcome* finansial bisa dikirimkan langsung dari *smartphone*.
- **🗔 Optimize Mode (Mini Overlay)**: Mode *compact* atau *Picture-in-Picture* agar antarmuka Amadeus melayang di sudut layar dan tidak menghalangi ruang kerja (*desktop*) saat sedang sibuk *coding*.
- **📝 Task & Deadline Manager**: Menambahkan fitur catatan (*notes*) dan integrasi kalender untuk pengingat tenggat waktu tugas (fitur krusial untuk bertahan hidup sebagai mahasiswa tingkat akhir).

## 🤝 Kontribusi
Ingin mengembangkan Amadeus lebih jauh? Jangan ragu untuk melakukan fork dan mengirimkan *Pull Request*. 

*El Psy Kongroo.*
