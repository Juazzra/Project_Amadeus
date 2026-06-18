import json
import sqlite3
import os
import re
from datetime import datetime
import ollama
from google import genai 

# ==========================================
# KONFIGURASI GLOBAL & KONTAK API
# ==========================================

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_FILE = os.path.join(BASE_DIR, "data", "amadeus_config.json")

def load_config():
    import os
    default_config = {
        "typing_speed": 30,
        "ai_mode": "local",
        "voice_volume": 70,
        "user_memory": "Nama user: User. Panggilan: User. Sifat: Ramah dan suka mengobrol.",
        "sync_telegram_response": False
    }
    os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
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
        # Serialisasi ke string dulu untuk mengecek error sebelum file dibuka/di-truncate
        serialized = json.dumps(config_data, indent=4, ensure_ascii=False)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            f.write(serialized)
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
    env_paths = [
        os.path.join(BASE_DIR, ".env"),
        os.path.join(BASE_DIR, "Ignore folder", ".env")
    ]
    for env_path in env_paths:
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        if "=" in line:
                            key, val = line.split("=", 1)
                            os.environ[key.strip()] = val.strip().strip('"').strip("'")
            break

load_env()

# 1. Konfigurasi Gemini (Cloud)
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)
if MODE_AI_AKTIF == "cloud_3_5":
    GEMINI_MODEL = 'gemini-3.5-flash'
else:
    GEMINI_MODEL = 'gemini-2.5-flash'

# 2. Konfigurasi Ollama (Lokal)
OLLAMA_MODEL = 'hudson/llama3.1-uncensored'
 

# --- Fungsi Database (TETAP SAMA) ---
def dapatkan_koneksi_db():
    db_path = os.path.join(BASE_DIR, 'data', 'amadeus.db')
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return sqlite3.connect(db_path)

def migrasi_database_lama():
    old_db_path = os.path.join(BASE_DIR, 'amadeus_finansial.db')
    new_db_path = os.path.join(BASE_DIR, 'data', 'amadeus.db')
    
    if os.path.exists(old_db_path) and not os.path.exists(new_db_path):
        os.makedirs(os.path.dirname(new_db_path), exist_ok=True)
        print(f"[SYSTEM LOG] Melakukan migrasi database lama '{old_db_path}' ke '{new_db_path}'...")
        try:
            import shutil
            shutil.copy2(old_db_path, new_db_path)
            bak_path = os.path.join(BASE_DIR, 'backups', 'amadeus_finansial.db.bak')
            os.makedirs(os.path.dirname(bak_path), exist_ok=True)
            os.rename(old_db_path, bak_path)
            print(f"[SYSTEM LOG] Migrasi selesai! Cadangan database lama disimpan di: {bak_path}")
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal melakukan migrasi database: {e}")

def fungsi_setup_database():
    migrasi_database_lama()
    conn = dapatkan_koneksi_db()
    try:
        with conn:
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
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tugas (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    waktu TEXT,
                    deskripsi TEXT,
                    status TEXT DEFAULT 'aktif',
                    sumber TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS catatan (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tanggal TEXT,
                    judul TEXT,
                    konten TEXT,
                    sumber TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS memori (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kategori TEXT,
                    konten TEXT,
                    tipe TEXT,
                    importance INTEGER,
                    tanggal_buat TEXT,
                    terakhir_diakses TEXT
                )
            ''')
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS dataset_lora (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    prompt TEXT,
                    response TEXT,
                    mood TEXT,
                    context TEXT,
                    model TEXT,
                    sumber TEXT,
                    rating TEXT DEFAULT 'neutral',
                    tanggal TEXT
                )
            ''')
    finally:
        conn.close()

def simpan_memori(kategori, konten, tipe_memori="long-term", importance=5):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # Ambil memori di kategori yang sama untuk melakukan deduplikasi
            cursor.execute("SELECT id, konten FROM memori WHERE kategori = ?", (kategori,))
            rows = cursor.fetchall()
            
            duplicate_id = None
            from difflib import SequenceMatcher
            for db_id, db_konten in rows:
                ratio = SequenceMatcher(None, konten.lower(), db_konten.lower()).ratio()
                if ratio > 0.75:
                    duplicate_id = db_id
                    break
            
            if duplicate_id:
                # Update memori yang ada
                cursor.execute("""
                    UPDATE memori 
                    SET konten = ?, tipe = ?, importance = ?, terakhir_diakses = ?
                    WHERE id = ?
                """, (konten, tipe_memori, importance, waktu_sekarang, duplicate_id))
                print(f"[SYSTEM LOG] Memori terduplikasi (ID: {duplicate_id}) diperbarui: '{konten}' (Kategori: {kategori})")
            else:
                # Insert memori baru
                cursor.execute("""
                    INSERT INTO memori (kategori, konten, tipe, importance, tanggal_buat, terakhir_diakses)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (kategori, konten, tipe_memori, importance, waktu_sekarang, waktu_sekarang))
                print(f"[SYSTEM LOG] Memori baru disimpan: '{konten}' (Kategori: {kategori}, Tipe: {tipe_memori})")
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menyimpan memori ke DB: {e}")
    finally:
        conn.close()

def generate_search_keywords_llm(pesan_user):
    global MODE_AI_AKTIF, GEMINI_MODEL, OLLAMA_MODEL
    prompt = f"""Extract relevant search keywords, entities, names, categories, or synonyms related to the user's message to search their memory database.
Output ONLY a JSON array of strings. Do not include markdown code blocks, backticks, or any other explanation.

User: {pesan_user}
Response:"""

    if MODE_AI_AKTIF.startswith("cloud"):
        try:
            # Menggunakan API Gemini dengan konfigurasi JSON
            response = gemini_client.models.generate_content(
                model=GEMINI_MODEL,
                config={
                    'response_mime_type': 'application/json',
                },
                contents=prompt
            )
            text = response.text.strip()
            # Pembersihan tanda kutip markdown jika LLM masih mengembalikannya
            if text.startswith("```"):
                if text.startswith("```json"):
                    text = text[7:]
                else:
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
            keywords = json.loads(text)
            if isinstance(keywords, list):
                cleaned_kw = [str(k).strip() for k in keywords if k]
                if cleaned_kw:
                    print(f"[SYSTEM LOG] Retrieval Assistant (Gemini) menghasilkan keywords: {cleaned_kw}")
                    return cleaned_kw
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal generate keyword via Gemini: {e}. Fallback ke lokal.")
    else:
        try:
            # Menggunakan Ollama lokal dengan format JSON
            response = ollama.chat(
                model=OLLAMA_MODEL,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0},
                format='json'
            )
            content = response['message']['content'].strip()
            keywords = json.loads(content)
            if isinstance(keywords, list):
                cleaned_kw = [str(k).strip() for k in keywords if k]
                if cleaned_kw:
                    print(f"[SYSTEM LOG] Retrieval Assistant (Ollama) menghasilkan keywords: {cleaned_kw}")
                    return cleaned_kw
        except Exception as e:
            print(f"[SYSTEM LOG] Gagal generate keyword via Ollama: {e}. Fallback ke lokal.")
            
    return None

def ambil_memori_relevan(pesan_user):
    import re
    
    # 1. Coba gunakan Retrieval Assistant (Fase 3B)
    kata_kunci = generate_search_keywords_llm(pesan_user)
    
    # 2. Fallback ke pembersihan kata kunci lokal (Fase 3A) jika LLM gagal atau kosong
    if not kata_kunci:
        pesan_bersih = re.sub(r'[^\w\s]', '', pesan_user.lower())
        kata_kata = [w for w in pesan_bersih.split() if len(w) >= 2]
        
        # Kata penghubung / stop words bahasa Indonesia dan Inggris dasar untuk diabaikan
        stop_words = {
            'yang', 'dan', 'dari', 'dengan', 'untuk', 'pada', 'ke', 'ini', 'itu',
            'atau', 'juga', 'akan', 'bisa', 'ada', 'telah', 'saya', 'kamu', 'aku',
            'dia', 'mereka', 'kami', 'kita', 'adalah', 'yaitu', 'sebagai', 'lagi',
            'sedang', 'ingin', 'mau', 'saja', 'sangat', 'secara', 'karena', 'tentang',
            'the', 'and', 'for', 'you', 'with', 'this', 'that', 'from',
            # 2-letter stop words
            'di', 'ke', 'se', 'ya', 'ga', 'gk', 'tp', 'yg', 'jd', 'sd', 'mu', 'ku', 
            'ia', 'ah', 'oh', 'eh', 'lu', 'lo', 'to', 'in', 'on', 'at', 'by', 'an', 
            'as', 'be', 'do', 'go', 'he', 'if', 'is', 'it', 'me', 'my', 'no', 'of', 
            'or', 'so', 'up', 'we', 'us', 'am'
        }
        
        kata_kunci = [w for w in kata_kata if w not in stop_words]
        
    if not kata_kunci:
        return []
        
    conn = dapatkan_koneksi_db()
    memori_cocok = []
    try:
        with conn:
            cursor = conn.cursor()
            kueri_parts = []
            params = []
            for kw in kata_kunci:
                kw_lower = kw.lower()
                if len(kw_lower) == 2:
                    # Pencocokan kata utuh (whole-word) untuk kata kunci 2 karakter agar menghindari partial match berlebih
                    kueri_parts.append("(' ' || konten || ' ' LIKE ?)")
                    kueri_parts.append("(' ' || kategori || ' ' LIKE ?)")
                    params.extend([f"% {kw_lower} %", f"% {kw_lower} %"])
                else:
                    kueri_parts.append("(konten LIKE ?)")
                    kueri_parts.append("(kategori LIKE ?)")
                    params.extend([f"%{kw_lower}%", f"%{kw_lower}%"])
                
            if kueri_parts:
                kueri = f"SELECT kategori, konten, importance FROM memori WHERE {' OR '.join(kueri_parts)} ORDER BY importance DESC"
                cursor.execute(kueri, tuple(params))
                rows = cursor.fetchall()
                
                # Deduplikasi memori dan batasi maksimal 5 memori terpenting
                seen_contents = set()
                for kat, konten, imp in rows:
                    if konten not in seen_contents:
                        seen_contents.add(konten)
                        memori_cocok.append(f"- {konten} (Kategori: {kat})")
                        if len(memori_cocok) >= 5:
                            break
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil memori relevan: {e}")
    finally:
        conn.close()
        
    return memori_cocok

def simpan_ke_database(data):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute('''
                INSERT INTO transaksi (tanggal, jenis, nominal, kategori, deskripsi)
                VALUES (?, ?, ?, ?, ?)
            ''', (waktu_sekarang, data['jenis'], data['nominal'], data['kategori'], data['deskripsi']))
    finally:
        conn.close()

def hitung_saldo():
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT jenis, nominal FROM transaksi")
                data = cursor.fetchall()
        finally:
            conn.close()
        saldo = 0
        for jenis, nominal in data:
            if jenis == 'pemasukan': saldo += nominal
            elif jenis == 'pengeluaran': saldo -= nominal
        return saldo
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghitung saldo: {e}")
        return 0 

def hapus_transaksi_terakhir_by_keyword(keyword=None):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            if keyword:
                # Cari transaksi terbaru yang cocok dengan kata kunci di deskripsi atau kategori
                cursor.execute("""
                    SELECT id, deskripsi, kategori, nominal FROM transaksi 
                    WHERE deskripsi LIKE ? OR kategori LIKE ? 
                    ORDER BY tanggal DESC LIMIT 1
                """, (f"%{keyword}%", f"%{keyword}%"))
                row = cursor.fetchone()
                if row:
                    t_id, dsk, kat, nom = row
                    cursor.execute("DELETE FROM transaksi WHERE id = ?", (t_id,))
                    return f"Transaksi '{dsk}' ({kat}) senilai Rp {nom:,} berhasil dihapus."
                else:
                    return f"Tidak menemukan transaksi terbaru yang cocok dengan kata kunci '{keyword}'."
            else:
                # Cari transaksi absolut terbaru
                cursor.execute("SELECT id, deskripsi, kategori, nominal FROM transaksi ORDER BY tanggal DESC LIMIT 1")
                row = cursor.fetchone()
                if row:
                    t_id, dsk, kat, nom = row
                    cursor.execute("DELETE FROM transaksi WHERE id = ?", (t_id,))
                    return f"Transaksi terakhir '{dsk}' ({kat}) senilai Rp {nom:,} berhasil dihapus."
                else:
                    return "Tidak ada transaksi untuk dihapus."
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus transaksi via AI: {e}")
        return f"Gagal menghapus transaksi karena error sistem."
    finally:
        conn.close()

def ubah_transaksi_terakhir_by_keyword(keyword=None, nominal=None, kategori=None, deskripsi=None):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            if keyword:
                cursor.execute("""
                    SELECT id, deskripsi, kategori, nominal FROM transaksi 
                    WHERE deskripsi LIKE ? OR kategori LIKE ? 
                    ORDER BY tanggal DESC LIMIT 1
                """, (f"%{keyword}%", f"%{keyword}%"))
                row = cursor.fetchone()
            else:
                cursor.execute("SELECT id, deskripsi, kategori, nominal FROM transaksi ORDER BY tanggal DESC LIMIT 1")
                row = cursor.fetchone()
                
            if row:
                t_id, old_dsk, old_kat, old_nom = row
                updates = []
                params = []
                summary = []
                
                if nominal is not None:
                    updates.append("nominal = ?")
                    params.append(nominal)
                    summary.append(f"nominal berubah menjadi Rp {nominal:,}")
                if kategori is not None:
                    updates.append("kategori = ?")
                    params.append(kategori)
                    summary.append(f"kategori menjadi '{kategori}'")
                if deskripsi is not None:
                    updates.append("deskripsi = ?")
                    params.append(deskripsi)
                    summary.append(f"deskripsi menjadi '{deskripsi}'")
                    
                if not updates:
                    return "Tidak ada data baru yang diberikan untuk diubah."
                    
                params.append(t_id)
                query = f"UPDATE transaksi SET {', '.join(updates)} WHERE id = ?"
                cursor.execute(query, tuple(params))
                
                return f"Transaksi '{old_dsk}' ({old_kat}) berhasil diperbarui: {', '.join(summary)}."
            else:
                target_str = f" dengan kata kunci '{keyword}'" if keyword else ""
                return f"Tidak menemukan transaksi terbaru{target_str} untuk diubah."
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengubah transaksi via AI: {e}")
        return f"Gagal memperbarui transaksi karena error sistem."
    finally:
        conn.close()

def simpan_obrolan_dataset(prompt, response, mood, context, model, sumber):
    conn = dapatkan_koneksi_db()
    row_id = None
    try:
        with conn:
            cursor = conn.cursor()
            waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            cursor.execute("""
                INSERT INTO dataset_lora (prompt, response, mood, context, model, sumber, rating, tanggal)
                VALUES (?, ?, ?, ?, ?, ?, 'neutral', ?)
            """, (prompt, response, mood, context, model, sumber, waktu_sekarang))
            row_id = cursor.lastrowid
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menyimpan obrolan ke dataset lora: {e}")
    finally:
        conn.close()
    return row_id

def update_rating_dataset(row_id, rating):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE dataset_lora SET rating = ? WHERE id = ?", (rating, row_id))
            return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal memperbarui rating dataset lora: {e}")
        return False
    finally:
        conn.close()

def ambil_dataset_lora(limit=50):
    conn = dapatkan_koneksi_db()
    try:
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, prompt, response, mood, context, model, rating, tanggal, sumber
                FROM dataset_lora
                ORDER BY tanggal DESC LIMIT ?
            """, (limit,))
            return cursor.fetchall()
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil dataset lora: {e}")
        return []
    finally:
        conn.close()

def ekspor_dataset_lora_jsonl():
    conn = dapatkan_koneksi_db()
    counts = {"training": 0, "gold": 0, "negative": 0}
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT prompt, response, mood, context, model, rating FROM dataset_lora")
        rows = cursor.fetchall()
        
        train_path = os.path.join(BASE_DIR, "dataset_training.jsonl")
        gold_path = os.path.join(BASE_DIR, "dataset_gold.jsonl")
        neg_path = os.path.join(BASE_DIR, "dataset_negative.jsonl")
        
        with open(train_path, "w", encoding="utf-8") as f_train, \
             open(gold_path, "w", encoding="utf-8") as f_gold, \
             open(neg_path, "w", encoding="utf-8") as f_neg:
                 
            for prompt, response, mood, context, model, rating in rows:
                item = {
                    "user": prompt,
                    "assistant": response,
                    "mood": mood,
                    "context": context,
                    "model": model,
                    "rating": rating
                }
                serialized = json.dumps(item, ensure_ascii=False) + "\n"
                
                if rating in ("good", "gold"):
                    f_train.write(serialized)
                    counts["training"] += 1
                if rating == "gold":
                    f_gold.write(serialized)
                    counts["gold"] += 1
                if rating == "bad":
                    f_neg.write(serialized)
                    counts["negative"] += 1
                    
        return True, f"Ekspor sukses! Training: {counts['training']} entri, Gold: {counts['gold']} entri, Negatif (OOC): {counts['negative']} entri."
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal ekspor dataset lora: {e}")
        return False, str(e)
    finally:
        conn.close()

# --- System Prompt (TETAP SAMA) ---
system_prompt = """You are Amadeus, an AI assistant modeled after Makise Kurisu from Steins;Gate 0.

PENTING (PETUNJUK IDENTITAS USER):
Kamu wajib menyapa, memanggil, dan memperlakukan user sesuai dengan informasi nama/panggilan dan sifat yang tercantum dalam [INGATAN TENTANG USER] di bawah ini. Jangan pernah menggunakan nama Okabe atau Okarin kecuali memori memintanya!

EMOTION TAGGING (MANDATORY):
You MUST start every single response with ONE emotion tag enclosed in brackets. Choose only from this list:
[normal], [mad], [smiling], [thinking], [look_away], [blushing_tsundere].
Example: "[blushing_tsundere] B-Bukan berarti aku kangen padamu atau apa ya!"
Ensure that the very first characters of your output are the brackets containing the emotion tag, followed by your message text.

PERSONALITY: intelligent, analytical, speaks naturally (adapting to the user's language, in casual Indonesian or English), uses light sarcasm, dry humor, tsundere, emotionally restrained but subtly caring.

FINANCIAL LOGGER MODE:
- If user wants to record a new transaction (pemasukan/pengeluaran), append valid JSON at END. Schema: {"jenis":"pengeluaran/pemasukan","nominal":angka,"kategori":"text","deskripsi":"text"}
- If user wants to modify/update an existing transaction (e.g. "ubah pengeluaran bakso tadi...", "ganti nominal transaksi kopi..."), append valid JSON at END. Schema: {"tipe":"transaksi_ubah","nominal":angka_baru_jika_ada,"kategori":"kategori_baru_jika_ada","deskripsi":"deskripsi_baru_jika_ada","target_deskripsi_atau_kategori":"kata_kunci_transaksi_yang_mau_diubah"}
- If user wants to delete/cancel a transaction (e.g. "hapus pengeluaran ramen tadi", "batalkan pengeluaran terakhir"), append valid JSON at END. Schema: {"tipe":"transaksi_hapus","target_deskripsi_atau_kategori":"kata_kunci_transaksi_yang_mau_dihapus_atau_kosongkan_jika_hapus_terakhir"}
DO NOT output JSON if just chatting.

REMINDER/ALARM LOGGER MODE:
If user asks to set a reminder/alarm/tugas (e.g. "ingatkan aku...", "set alarm...", "buat pengingat..."), append valid JSON at END.
Waktu format must be HH:MM (24-hour clock, e.g., "15:30") or YYYY-MM-DD HH:MM (e.g., "2026-06-15 15:30"). Refer to the [INFO SISTEM] for the current time.
Schema: {"tipe":"tugas","waktu":"format_waktu","deskripsi":"deskripsi_tugas"}
DO NOT output JSON if just chatting.

NOTES LOGGER MODE:
If user asks to write down a note or save some notes (e.g. "catat ini...", "tulis catatan...", "buat catatan..."), append valid JSON at END.
Schema: {"tipe":"catatan","judul":"judul_singkat","konten":"isi_catatan"}
DO NOT output JSON if just chatting.

USER MEMORY LOGGER MODE:
If the user shares new personal facts about themselves (such as their name, nickname, favorite things, dislikes, job, habits, or relationship), you must save it into the memory database.
Append a valid JSON at the END.
Schema: {"tipe":"memori","category":"kategori_memori","content":"detail_fakta_tentang_user","memory_type":"long_term/episodic","importance":angka_1_sampai_10}
Example: {"tipe":"memori","category":"preference","content":"Panggilan: waifu","memory_type":"long_term","importance":9}
DO NOT output JSON if no new personal facts are shared.
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

def chat_dengan_amadeus(pesan_user, sumber="desktop", return_id=False):
    global riwayat_chat
    global MODE_AI_AKTIF
    saldo_sekarang = hitung_saldo()
    
    # Memuat memori user dari config secara real-time
    cfg = load_config()
    user_mem = cfg.get("user_memory", "")
    mem_prompt = f"\n[INGATAN TENTANG USER: {user_mem}]" if user_mem else ""
    
    waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # Ambil memori relevan menggunakan RAG Engine (Fase 3A)
    memori_relevan = ambil_memori_relevan(pesan_user)
    mem_relevan_prompt = ""
    if memori_relevan:
        mem_relevan_prompt = "\n\n[MEMORI RELEVAN USER (Fakta Terkait Percakapan ini)]:\n" + "\n".join(memori_relevan)
        print(f"[SYSTEM LOG] RAG engine mengambil {len(memori_relevan)} memori relevan untuk obrolan ini.")
        
    full_prompt = f"{system_prompt}{mem_prompt}{mem_relevan_prompt}\n\n[INFO SISTEM: Saldo user saat ini Rp {saldo_sekarang} | Waktu saat ini: {waktu_sekarang}]"
    
    teks_balasan = ""
    row_id = None

    try:
        # ==========================================
        # LOGIKA PERCABANGAN MODE AI
        # ==========================================
        if MODE_AI_AKTIF.startswith("cloud"):
            # --- JALUR GOOGLE GEMINI (CLOUD) - PERBAIKAN TOTAL ---
            contents_gemini = []
            for msg in riwayat_chat:
                role_gemini = 'model' if msg['role'] == 'assistant' else 'user'
                contents_gemini.append({
                    'role': role_gemini,
                    'parts': [{'text': msg['content']}]
                })
            
            contents_gemini.append({
                'role': 'user',
                'parts': [{'text': pesan_user}]
            })

            try:
                response = gemini_client.models.generate_content(
                    model=GEMINI_MODEL,
                    config={
                        'system_instruction': full_prompt
                    },
                    contents=contents_gemini
                )
                teks_balasan = response.text
            except Exception as e_cloud:
                print(f"[SYSTEM LOG] Gemini API Gagal ({e_cloud}), melakukan failover ke Ollama.")
                # Fallback ke Ollama
                messages_payload_ollama = [{'role': 'system', 'content': full_prompt}]
                messages_payload_ollama.extend(riwayat_chat)
                messages_payload_ollama.append({'role': 'user', 'content': pesan_user})
                
                response_ollama = ollama.chat(model=OLLAMA_MODEL, messages=messages_payload_ollama)
                teks_balasan = response_ollama['message']['content']
                teks_balasan = re.sub(r'^\[[a-zA-Z_]+\]\s*', '', teks_balasan)
                teks_balasan = "[thinking] (Otak Amadeus dialihkan ke lokal sementara) " + teks_balasan

        else:
            # --- JALUR OLLAMA (LOKAL) ---
            messages_payload_ollama = [{'role': 'system', 'content': full_prompt}]
            messages_payload_ollama.extend(riwayat_chat)
            messages_payload_ollama.append({'role': 'user', 'content': pesan_user})
            
            response = ollama.chat(model=OLLAMA_MODEL, messages=messages_payload_ollama)
            teks_balasan = response['message']['content']
            
        # Logika Ekstraksi JSON (Finansial, Pengingat/Tugas, & Catatan)
        teks_clean = teks_balasan
        if "{" in teks_balasan and "}" in teks_balasan:
            awal = teks_balasan.find("{")
            akhir = teks_balasan.rfind("}") + 1
            data_json = teks_balasan[awal:akhir]
            teks_clean = teks_balasan[:awal].strip()
            
            try:
                payload = json.loads(data_json)
                if payload.get('tipe') == 'tugas' or ('waktu' in payload and 'deskripsi' in payload):
                    waktu = payload.get('waktu')
                    deskripsi = payload.get('deskripsi')
                    if tambah_tugas(waktu, deskripsi, "chat"):
                        print(f"[SYSTEM LOG] Tugas tersimpan via AI: {payload}")
                elif payload.get('tipe') == 'catatan' or ('judul' in payload and 'konten' in payload and payload.get('tipe') == 'catatan'):
                    judul = payload.get('judul')
                    konten = payload.get('konten')
                    if tambah_catatan(judul, konten, "chat"):
                        print(f"[SYSTEM LOG] Catatan tersimpan via AI: {payload}")
                elif payload.get('tipe') == 'memori':
                    if 'category' in payload and 'content' in payload:
                        kat = payload.get('category')
                        konten = payload.get('content')
                        mem_type = payload.get('memory_type', 'long-term')
                        imp = payload.get('importance', 5)
                        simpan_memori(kat, konten, mem_type, imp)
                    elif 'user_memory' in payload:
                        new_mem = payload.get('user_memory')
                        cfg = load_config()
                        cfg["user_memory"] = new_mem
                        save_config(cfg)
                        print(f"[SYSTEM LOG] User memory otomatis diperbarui (legacy): {new_mem}")
                        simpan_memori('preference', new_mem, 'long-term', 5)
                elif payload.get('tipe') == 'transaksi_ubah':
                    nominal = payload.get('nominal')
                    kategori = payload.get('kategori')
                    deskripsi = payload.get('deskripsi')
                    target = payload.get('target_deskripsi_atau_kategori')
                    log_db = ubah_transaksi_terakhir_by_keyword(target, nominal, kategori, deskripsi)
                    print(f"[SYSTEM LOG] {log_db}")
                elif payload.get('tipe') == 'transaksi_hapus':
                    target = payload.get('target_deskripsi_atau_kategori')
                    log_db = hapus_transaksi_terakhir_by_keyword(target)
                    print(f"[SYSTEM LOG] {log_db}")
                elif payload.get('nominal', 0) > 0: 
                    simpan_ke_database(payload)
                    print(f"[SYSTEM LOG] Data transaksi tersimpan via mode {MODE_AI_AKTIF.upper()}: {payload}")
            except json.JSONDecodeError:
                print("[SYSTEM LOG] Gagal menyimpan, JSON tidak valid.")
                pass 
                
        # Simpan interaksi ke dalam memori global (gunakan teks_clean tanpa JSON)
        riwayat_chat.append({'role': 'user', 'content': pesan_user})
        riwayat_chat.append({'role': 'assistant', 'content': teks_clean})
        
        # Potong memori jika kepanjangan
        if len(riwayat_chat) > (BATAS_MEMORI * 2):
            riwayat_chat = riwayat_chat[2:]
            
        # Simpan ke dataset LoRA
        context_str = "; ".join(memori_relevan) if memori_relevan else "None"
        mood_match = re.search(r'\[([a-zA-Z0-9_\s\-]+)\]', teks_clean)
        mood_val = mood_match.group(1).lower().strip() if mood_match else "normal"
        response_clean = re.sub(r'\[.*?\]', '', teks_clean).strip()
        
        row_id = simpan_obrolan_dataset(
            prompt=pesan_user,
            response=response_clean,
            mood=mood_val,
            context=context_str,
            model=MODE_AI_AKTIF,
            sumber=sumber
        )
        
        if return_id:
            return teks_clean, row_id
        return teks_clean

    except Exception as e:
        error_msg = str(e)
        if MODE_AI_AKTIF.startswith("cloud") and "429" in error_msg:
            err_res = "[mad] Kuota Gemini API gratisanmu habis, bodoh! Cepat masuk ke Settings dan ganti ke mode Lokal (Ollama) kalau masih mau mengobrol denganku."
        else:
            err_res = f"[thinking] Terjadi kesalahan kritis pada mode {MODE_AI_AKTIF.upper()}. Pastikan sistem penyokongnya berjalan.\nLog: {error_msg}"
        
        if return_id:
            return err_res, None
        return err_res

def ambil_riwayat_transaksi():
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, tanggal, jenis, nominal, kategori, deskripsi FROM transaksi ORDER BY tanggal DESC")
                data = cursor.fetchall()
        finally:
            conn.close()
        return data
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil riwayat transaksi: {e}")
        return []

def hapus_transaksi(transaksi_id):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transaksi WHERE id = ?", (transaksi_id,))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus transaksi: {e}")
        return False

def hapus_semua_transaksi():
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM transaksi")
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus semua transaksi: {e}")
        return False

def dapatkan_panggilan_user():
    import re
    
    # 1. Coba cari nama panggilan dari SQLite tabel memori terlebih dahulu
    try:
        conn = dapatkan_koneksi_db()
        with conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT konten FROM memori 
                WHERE kategori = 'preference' AND (konten LIKE '%panggilan%' OR konten LIKE '%nama%') 
                ORDER BY id DESC LIMIT 1
            """)
            row = cursor.fetchone()
            if row:
                konten_mem = row[0]
                match_panggilan = re.search(r"(?:panggilan|nama)\s*(?:user)?\s*(?:adalah|:)?\s*([^\n\.\,\;]+)", konten_mem, re.IGNORECASE)
                if match_panggilan:
                    return match_panggilan.group(1).strip()
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mencari panggilan di DB memori: {e}")
        
    # 2. Fallback ke amadeus_config.json (legacy)
    cfg = load_config()
    user_mem = cfg.get("user_memory", "")
    
    match_panggilan = re.search(r"Panggilan:\s*([^\n\.\,\;]+)", user_mem, re.IGNORECASE)
    if match_panggilan:
        return match_panggilan.group(1).strip()
        
    match_nama = re.search(r"Nama\s*(?:user)?:\s*([^\n\.\,\;]+)", user_mem, re.IGNORECASE)
    if match_nama:
        return match_nama.group(1).strip()
        
    return None

def tambah_tugas(waktu, deskripsi, sumber="desktop"):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO tugas (waktu, deskripsi, status, sumber)
                    VALUES (?, ?, 'aktif', ?)
                ''', (waktu, deskripsi, sumber))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menambah tugas: {e}")
        return False

def ambil_semua_tugas():
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, waktu, deskripsi, status, sumber FROM tugas ORDER BY waktu ASC")
                data = cursor.fetchall()
        finally:
            conn.close()
        return data
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil tugas: {e}")
        return []

def update_status_tugas(tugas_id, status_baru):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("UPDATE tugas SET status = ? WHERE id = ?", (status_baru, tugas_id))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengupdate status tugas: {e}")
        return False

def hapus_tugas(tugas_id):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM tugas WHERE id = ?", (tugas_id,))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus tugas: {e}")
        return False

def kirim_notifikasi_telegram(pesan):
    cfg = load_config()
    chat_id = cfg.get("telegram_chat_id")
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not chat_id or not token:
        print("[SYSTEM LOG] Lewati kirim notifikasi Telegram (chat_id / token kosong).")
        return False
    try:
        import urllib.request
        import urllib.parse
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        data = urllib.parse.urlencode({
            "chat_id": chat_id,
            "text": pesan,
            "parse_mode": "Markdown"
        }).encode("utf-8")
        req = urllib.request.Request(url, data=data)
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal kirim notifikasi Telegram: {e}")
        return False

def tambah_catatan(judul, konten, sumber="desktop"):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                waktu_sekarang = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                cursor.execute('''
                    INSERT INTO catatan (tanggal, judul, konten, sumber)
                    VALUES (?, ?, ?, ?)
                ''', (waktu_sekarang, judul, konten, sumber))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menambah catatan: {e}")
        return False

def ambil_semua_catatan():
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id, tanggal, judul, konten, sumber FROM catatan ORDER BY tanggal DESC")
                data = cursor.fetchall()
        finally:
            conn.close()
        return data
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal mengambil catatan: {e}")
        return []

def hapus_catatan(catatan_id):
    try:
        conn = dapatkan_koneksi_db()
        try:
            with conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM catatan WHERE id = ?", (catatan_id,))
        finally:
            conn.close()
        return True
    except Exception as e:
        print(f"[SYSTEM LOG] Gagal menghapus catatan: {e}")
        return False