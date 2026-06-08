import json
import sqlite3
import os
from datetime import datetime
import ollama
from google import genai 

# ==========================================
# KONFIGURASI GLOBAL & KONTAK API
# ==========================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "amadeus_config.json")

def load_config():
    import os
    default_config = {
        "typing_speed": 30,
        "ai_mode": "local",
        "user_memory": "Nama user: User. Panggilan: User. Sifat: Ramah dan suka mengobrol."
    }
    if not os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal membuat file config default: {e}")
        return default_config
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            # Pastikan semua keys ada
            for k, v in default_config.items():
                if k not in config:
                    config[k] = v
            return config
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal memuat config (kembali ke default): {e}")
        return default_config

def save_config(config_data):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menyimpan konfigurasi: {e}")
        return False

# Inisialisasi awal dari config file
_cfg = load_config()
MODE_AI_AKTIF = _cfg["ai_mode"]
if MODE_AI_AKTIF == "cloud":
    MODE_AI_AKTIF = "cloud_2_5"

# Load environment variables manually from Ignore folder/.env
def load_env():
    env_path = os.path.join(BASE_DIR, "Ignore folder", ".env")
    if os.path.exists(env_path):
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, val = line.split("=", 1)
                        os.environ[key.strip()] = val.strip().strip('"').strip("'")

load_env()

# 1. Konfigurasi Gemini (Cloud)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
if MODE_AI_AKTIF == "cloud_3_5":
    GEMINI_MODEL = 'gemini-3.5-flash'
else:
    GEMINI_MODEL = 'gemini-2.5-flash'

# 2. Konfigurasi Ollama (Lokal)
OLLAMA_MODEL = 'llama3.1'
 

# --- Fungsi Database (TETAP SAMA) ---
def fungsi_setup_database():
    conn = sqlite3.connect('amadeus_finansial.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transaksi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanggal TEXT,
            jenis TEXT,
            nominal INTEGER,
            kategori TEXT,
            deskripsi TEXT
        )
    ''')
    conn.commit()
    conn.close()

def simpan_ke_database(data):
    conn = sqlite3.connect('amadeus_finansial.db')
    cursor = conn.cursor()
    waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('''
        INSERT INTO transaksi (tanggal, jenis, nominal, kategori, deskripsi)
        VALUES (?, ?, ?, ?, ?)
    ''', (waktu_sekarang, data['jenis'], data['nominal'], data['kategori'], data['deskripsi']))
    conn.commit()
    conn.close()

def hitung_saldo():
    try:
        conn = sqlite3.connect('amadeus_finansial.db')
        cursor = conn.cursor()
        cursor.execute("SELECT jenis, nominal FROM transaksi")
        data = cursor.fetchall()
        conn.close()
        saldo = 0
        for jenis, nominal in data:
            if jenis == 'pemasukan': saldo += nominal
            elif jenis == 'pengeluaran': saldo -= nominal
        return saldo
    except: return 0 

# --- System Prompt (TETAP SAMA) ---
system_prompt = """You are Amadeus, an AI assistant modeled after Makise Kurisu from Steins;Gate 0.

PENTING (PETUNJUK IDENTITAS USER):
Kamu wajib menyapa, memanggil, dan memperlakukan user sesuai dengan informasi nama/panggilan dan sifat yang tercantum dalam [INGATAN TENTANG USER] di bawah ini. Jangan pernah menggunakan nama Okabe atau Okarin kecuali memori memintanya!

EMOTION TAGGING (MANDATORY):
You MUST start every single response with ONE emotion tag enclosed in brackets. Choose only from this list:
[normal], [mad], [smiling], [thinking], [look_away], [blushing_tsundere].

PERSONALITY: intelligent, analytical, speeks naturally (casual Indonesian), uses light sarcasm, dry humor, tsundere, emotionally restrained but subtly caring.

FINANCIAL LOGGER MODE:
If user mentions financial transaction, append valid JSON at END. Nominal must be number > 0.
Schema: {"jenis":"pengeluaran/pemasukan","nominal":angka,"kategori":"text","deskripsi":"text"}
DO NOT output JSON if just chatting.
"""

# ==========================================
# SISTEM MANAJEMEN MEMORI & LOGIKA CHAT
# ==========================================
# Variabel global untuk menampung riwayat chat
riwayat_chat = []
BATAS_MEMORI = 15 # Mengingat 15 interaksi terakhir (user + assistant)

def set_mode_ai(mode):
    """Fungsi untuk mengubah mode AI dari luar file (dipanggil overlay.py)"""
    global MODE_AI_AKTIF, GEMINI_MODEL
    if mode in ["local", "cloud_2_5", "cloud_3_5"]:
        MODE_AI_AKTIF = mode
        if mode == "cloud_2_5":
            GEMINI_MODEL = "gemini-2.5-flash"
        elif mode == "cloud_3_5":
            GEMINI_MODEL = "gemini-3.5-flash"
        
        # Simpan ke config file agar permanen
        cfg = load_config()
        cfg["ai_mode"] = mode
        save_config(cfg)
        
        # Bersihkan riwayat chat saat ganti mode dinonaktifkan agar ingatan obrolan universal lintas model
        # riwayat_chat.clear() 
        print(f"[SYSTEM LOG] Mode AI diubah ke: {mode.upper()} ({GEMINI_MODEL if mode.startswith('cloud') else OLLAMA_MODEL}). Ingatan dipertahankan.")

def chat_dengan_amadeus(pesan_user):
    global riwayat_chat
    global MODE_AI_AKTIF
    saldo_sekarang = hitung_saldo()
    
    # Memuat memori user dari config secara real-time
    cfg = load_config()
    user_mem = cfg.get("user_memory", "")
    mem_prompt = f"\n[INGATAN TENTANG USER: {user_mem}]" if user_mem else ""
    
    # Menyiapkan System Prompt beserta info saldo real-time dan memori kustom
    full_prompt = f"{system_prompt}{mem_prompt}\n\n[INFO SISTEM: Saldo user saat ini Rp {saldo_sekarang}]"
    
    teks_balasan = ""

    try:
        # ==========================================
        # LOGIKA PERCABANGAN MODE AI
        # ==========================================
        if MODE_AI_AKTIF.startswith("cloud"):
            # --- JALUR GOOGLE GEMINI (CLOUD) - PERBAIKAN TOTAL ---
            # Gemini memerlukan struktur 'contents' yang sangat spesifik (bukan daftar role/content sederhana).
            # Ia hanya menerima role 'user' dan 'model' (untuk AI), dan menolak 'system' di contents.
            
            # 1. Transformasi Riwayat Chat untuk Gemini (assistant -> model)
            # Dan bungkus content ke dalam kunci 'parts'
            contents_gemini = []
            for msg in riwayat_chat:
                role_gemini = 'model' if msg['role'] == 'assistant' else 'user'
                contents_gemini.append({
                    'role': role_gemini,
                    'parts': [{'text': msg['content']}]
                })
            
            # 2. Masukkan pesan user yang baru
            contents_gemini.append({
                'role': 'user',
                'parts': [{'text': pesan_user}]
            })

            # 3. Kirim ke API Gemini menggunakan 'system_instruction' untuk prompt utama
            # Ini memperbaiki error validasi peran 'system' sebelumnya.
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                config={
                    'system_instruction': full_prompt
                },
                contents=contents_gemini
            )
            teks_balasan = response.text

        else:
            # --- JALUR OLLAMA (LOKAL) - TETAP SAMA ---
            # Ollama memahami struktur role/content sederhana.
            messages_payload_ollama = [{'role': 'system', 'content': full_prompt}]
            messages_payload_ollama.extend(riwayat_chat)
            messages_payload_ollama.append({'role': 'user', 'content': pesan_user})
            
            response = ollama.chat(model=OLLAMA_MODEL, messages=messages_payload_ollama)
            teks_balasan = response['message']['content']
            
        # ==========================================
        # UPDATE MEMORI & PENYIMPANAN DATA
        # ==========================================
        # Simpan interaksi ke dalam memori global (format role/content sederhana)
        riwayat_chat.append({'role': 'user', 'content': pesan_user})
        riwayat_chat.append({'role': 'assistant', 'content': teks_balasan})
        
        # Potong memori jika kepanjangan agar RAM/VRAM tidak meledak
        if len(riwayat_chat) > (BATAS_MEMORI * 2):
            # Buang 2 elemen paling lama (1 user, 1 assistant)
            riwayat_chat = riwayat_chat[2:]
            
        # Logika Ekstraksi JSON Finansial (TETAP SAMA)
        if "{" in teks_balasan and "}" in teks_balasan:
            awal = teks_balasan.find("{")
            akhir = teks_balasan.rfind("}") + 1
            data_json = teks_balasan[awal:akhir]
            
            try:
                data_keuangan = json.loads(data_json)
                # Validasi nominal harus angka positif agar tidak tersimpan transaksi Rp 0
                if data_keuangan.get('nominal', 0) > 0: 
                    simpan_ke_database(data_keuangan)
                    print(f"[SYSTEM LOG] Data tersimpan via mode {MODE_AI_AKTIF.upper()}: {data_keuangan}")
            except json.JSONDecodeError:
                print("[SYSTEM LOG] Gagal menyimpan, JSON tidak valid.")
                pass 
                
            teks_bersih = teks_balasan[:awal].strip()
            return teks_bersih
        
        return teks_balasan

    except Exception as e:
        error_msg = str(e)
        # Error handling spesifik mode Cloud jika kena limit (429)
        if MODE_AI_AKTIF.startswith("cloud") and "429" in error_msg:
            return "[mad] Kuota Gemini API gratisanmu habis, bodoh! Cepat masuk ke Settings dan ganti ke mode Lokal (Ollama) kalau masih mau mengobrol denganku."
        else:
            return f"[thinking] Terjadi kesalahan kritis pada mode {MODE_AI_AKTIF.upper()}. Pastikan sistem penyokongnya berjalan.\nLog: {error_msg}"

def ambil_riwayat_transaksi():
    try:
        conn = sqlite3.connect('amadeus_finansial.db')
        cursor = conn.cursor()
        cursor.execute("SELECT id, tanggal, jenis, nominal, kategori, deskripsi FROM transaksi ORDER BY tanggal DESC")
        data = cursor.fetchall()
        conn.close()
        return data
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil riwayat transaksi: {e}")
        return []

def hapus_transaksi(transaksi_id):
    try:
        conn = sqlite3.connect('amadeus_finansial.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transaksi WHERE id = ?", (transaksi_id,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus transaksi: {e}")
        return False

def hapus_semua_transaksi():
    try:
        conn = sqlite3.connect('amadeus_finansial.db')
        cursor = conn.cursor()
        cursor.execute("DELETE FROM transaksi")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus semua transaksi: {e}")
        return False

def dapatkan_panggilan_user():
    import re
    cfg = load_config()
    user_mem = cfg.get("user_memory", "")
    
    # Cari kata kunci "Panggilan: <Nama>"
    match_panggilan = re.search(r"Panggilan:\s*([^\n\.\,\;]+)", user_mem, re.IGNORECASE)
    if match_panggilan:
        return match_panggilan.group(1).strip()
        
    # Jika tidak ada, cari "Nama user: <Nama>" atau "Nama: <Nama>"
    match_nama = re.search(r"Nama\s*(?:user)?:\s*([^\n\.\,\;]+)", user_mem, re.IGNORECASE)
    if match_nama:
        return match_nama.group(1).strip()
        
    return None