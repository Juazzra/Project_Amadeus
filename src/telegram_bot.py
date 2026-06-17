import os
import logging
import re
import functools
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import core
from core import chat_dengan_amadeus, fungsi_setup_database

# Thread-safe queue for logging to GUI (populated by overlay.py)
log_queue = None

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get Token from Environment
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")

def restricted(func):
    @functools.wraps(func)
    async def wrapped(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id if update.effective_user else None
        
        # Memuat env terbaru secara dinamis agar perubahan .env langsung berefek
        core.load_env()
        
        allowed_ids_str = os.environ.get("ALLOWED_TELEGRAM_USER_IDS", "")
        if allowed_ids_str:
            allowed_ids = [int(x.strip()) for x in allowed_ids_str.split(",") if x.strip().isdigit()]
            if user_id not in allowed_ids:
                logger.warning(f"[SECURITY] Percobaan akses tidak sah oleh user ID: {user_id}")
                
                panggilan = core.dapatkan_panggilan_user()
                panggilan_str = f" {panggilan}" if panggilan else ""
                
                msg_text = (
                    f"⚠️ *[AMADEUS SECURITY SYSTEM]*\n\n"
                    f"Akses ditolak! Kamu tidak terdaftar sebagai pemilik sistem Amadeus{panggilan_str}.\n"
                    f"ID Telegram Kamu: `{user_id}`\n\n"
                    f"Silakan tambahkan ID tersebut ke variabel `ALLOWED_TELEGRAM_USER_IDS` di file `.env` sistem Anda untuk memberikan izin."
                )
                
                if update.callback_query:
                    await update.callback_query.answer(text="Akses ditolak!", show_alert=True)
                    await update.effective_message.reply_text(msg_text, parse_mode="Markdown")
                else:
                    await update.message.reply_text(msg_text, parse_mode="Markdown")
                return
        else:
            # Jika kosong, beri peringatan di log console tapi izinkan akses
            logger.warning("[SECURITY WARNING] ALLOWED_TELEGRAM_USER_IDS kosong. Bot berjalan dalam mode publik.")
            
        return await func(update, context, *args, **kwargs)
    return wrapped

def save_chat_id(chat_id):
    cfg = core.load_config()
    if cfg.get("telegram_chat_id") != chat_id:
        cfg["telegram_chat_id"] = chat_id
        core.save_config(cfg)

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message when the command /start is issued."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    panggilan = core.dapatkan_panggilan_user()
    if panggilan:
        welcome_text = (
            f"Hallo {panggilan}! Aku Amadeus, asisten virtualmu.\n\n"
            "Gunakan menu berikut untuk mengontrolku:\n"
            "⚡ /settings - Lihat pengaturan saat ini\n"
            "🧠 /model - Ganti otak AI\n"
            "💳 /saldo - Cek saldo finansial\n"
            "📝 /riwayat - Lihat 5 transaksi terbaru\n"
            "👤 /memory - Lihat/ubah memori tentangmu\n\n"
            "Ketik /help untuk panduan lengkap penggunaan."
        )
    else:
        welcome_text = (
            "Hallo! Aku Amadeus, asisten virtualmu.\n\n"
            "Gunakan menu berikut untuk mengontrolku:\n"
            "⚡ /settings - Lihat pengaturan saat ini\n"
            "🧠 /model - Ganti otak AI\n"
            "💳 /saldo - Cek saldo finansial\n"
            "📝 /riwayat - Lihat 5 transaksi terbaru\n"
            "👤 /memory - Lihat/ubah memori tentangmu\n\n"
            "Ketik /help untuk panduan lengkap penggunaan."
        )
    await update.message.reply_text(welcome_text)

@restricted
async def set_model_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send an inline keyboard to choose the AI model."""
    keyboard = [
        [
            InlineKeyboardButton("Lokal (Ollama)", callback_data="local"),
            InlineKeyboardButton("Gemini 2.5", callback_data="cloud_2_5"),
            InlineKeyboardButton("Gemini 3.5", callback_data="cloud_3_5"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_mode = core.MODE_AI_AKTIF
    if current_mode == "local":
        mode_text = "Lokal (Ollama)"
    elif current_mode == "cloud_2_5":
        mode_text = "Gemini 2.5"
    else:
        mode_text = "Gemini 3.5"
        
    await update.message.reply_text(
        f"Otak AI Amadeus saat ini: *{mode_text}*\n\nPilih otak AI yang ingin digunakan:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

@restricted
async def model_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries from the inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    selected_mode = query.data
    # Apply AI mode update to configuration and core
    core.set_mode_ai(selected_mode)
    
    if selected_mode == "local":
        mode_text = "Lokal (Ollama)"
    elif selected_mode == "cloud_2_5":
        mode_text = "Gemini 2.5"
    else:
        mode_text = "Gemini 3.5"
        
    await query.edit_message_text(
        text=f"✓ Otak AI Amadeus berhasil diubah ke: *{mode_text}*.",
        parse_mode="Markdown"
    )

def get_rate_keyboard(row_id):
    if row_id is None:
        return None
    keyboard = [
        [
            InlineKeyboardButton("⭐ Emas", callback_data=f"rate_lora:{row_id}:gold"),
            InlineKeyboardButton("👍 Kurisu", callback_data=f"rate_lora:{row_id}:good"),
            InlineKeyboardButton("😐 Biasa", callback_data=f"rate_lora:{row_id}:neutral"),
            InlineKeyboardButton("👎 OOC", callback_data=f"rate_lora:{row_id}:bad")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

@restricted
async def rate_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle rating clicks for dataset lora."""
    query = update.callback_query
    await query.answer()
    
    parts = query.data.split(":")
    if len(parts) == 3:
        row_id = int(parts[1])
        rating = parts[2]
        
        success = core.update_rating_dataset(row_id, rating)
        if success:
            rating_map = {
                "gold": "⭐ Dataset Emas (Gold)",
                "good": "👍 Kurisu Banget (Good)",
                "neutral": "😐 Biasa Aja (Neutral)",
                "bad": "👎 Out of Character (Bad)"
            }
            rating_text = rating_map.get(rating, rating)
            text = query.message.text or ""
            new_text = f"{text}\n\n[Penilaian: {rating_text}]"
            await query.edit_message_text(text=new_text, reply_markup=None)

@restricted
async def saldo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the current financial balance."""
    saldo = core.hitung_saldo()
    await update.message.reply_text(f"💳 *Saldo Amadeus saat ini:*\nRp {saldo:,}", parse_mode="Markdown")

@restricted
async def riwayat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display the last 5 transactions."""
    records = core.ambil_riwayat_transaksi()
    if not records:
        await update.message.reply_text("Tidak ada riwayat transaksi yang ditemukan.")
        return
        
    lines = ["📝 *5 Transaksi Terakhir:*"]
    for r_id, tgl, jns, nom, kat, dsk in records[:5]:
        emoji = "🟢" if jns.lower() == "pemasukan" else "🔴"
        lines.append(f"{emoji} {tgl[:10]} | {kat} | *Rp {nom:,}* ({dsk})")
        
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

@restricted
async def memory_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View or update user memory."""
    args = context.args
    cfg = core.load_config()
    
    if not args:
        current_mem = cfg.get("user_memory", "Kosong")
        panggilan = core.dapatkan_panggilan_user()
        await update.message.reply_text(
            f"👤 *Ingatan Tentang User:*\n{current_mem}\n\n"
            f"Panggilan terdeteksi: *{panggilan or 'Tidak ada'}*\n\n"
            f"Untuk memperbarui ingatan, gunakan perintah:\n"
            f"`/memory <informasi baru>`",
            parse_mode="Markdown"
        )
    else:
        new_mem = " ".join(args)
        cfg["user_memory"] = new_mem
        core.save_config(cfg)
        
        # Reset current memory history to apply the new memory instantly
        core.riwayat_chat.clear()
        
        await update.message.reply_text(
            f"✓ *Ingatan berhasil diperbarui!*\nIngatan baru: {new_mem}\n"
            f"_Sesi percakapan di-reset agar ingatan baru langsung diterapkan._",
            parse_mode="Markdown"
        )

@restricted
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display current configurations."""
    cfg = core.load_config()
    mode = cfg.get("ai_mode", "local")
    speed = cfg.get("typing_speed", 30)
    user_mem = cfg.get("user_memory", "")
    
    if mode == "local":
        mode_text = "Lokal (Ollama)"
    elif mode == "cloud_2_5":
        mode_text = "Gemini 2.5"
    else:
        mode_text = "Gemini 3.5"
        
    await update.message.reply_text(
        f"⚙️ *Konfigurasi Sistem Amadeus:*\n\n"
        f"🧠 *Otak AI:* {mode_text}\n"
        f"⚡ *Typing Speed (GUI):* {speed} ms/char\n"
        f"👤 *User Memory:* {user_mem[:100]}...\n\n"
        f"Gunakan `/model` untuk mengganti mode AI,\n"
        f"dan `/memory` untuk mengubah ingatan Kurisu tentang Anda.",
        parse_mode="Markdown"
    )

@restricted
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the user message and query Amadeus AI."""
    user_text = update.message.text
    if not user_text:
        return
        
    # Cache chat ID
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    # Fetch response from Amadeus core
    reply_text, row_id = chat_dengan_amadeus(user_text, sumber="telegram", return_id=True)
    
    # Extract mood tag if any
    mood_match = re.search(r'\[([a-zA-Z0-9_\s\-]+)\]', reply_text)
    mood = mood_match.group(1).lower().strip() if mood_match else "normal"
    
    # Strip visual VN emotion tags (e.g., [normal], [mad]) for clean Telegram bubble chat
    reply_text_clean = re.sub(r'\[.*?\]', '', reply_text).strip()
    
    # Log structured interaction to GUI
    if log_queue is not None:
        log_queue.put({
            "type": "telegram_chat",
            "user_text": user_text,
            "reply_text": reply_text_clean,
            "mood": mood
        })
        
    await update.message.reply_text(reply_text_clean, reply_markup=get_rate_keyboard(row_id))

@restricted
async def tugas_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tugas command to list or add reminders."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args:
        # Tampilkan daftar tugas aktif
        tugas_list = core.ambil_semua_tugas()
        aktif_tugas = [t for t in tugas_list if t[3] == 'aktif']
        
        panggilan = core.dapatkan_panggilan_user()
        panggilan_str = f" {panggilan}" if panggilan else ""
        
        lines = [f"⏰ *Daftar Pengingat Amadeus Untuk{panggilan_str}:*"]
        if not aktif_tugas:
            lines.append("_Belum ada pengingat aktif._")
        else:
            for t_id, waktu, deskripsi, status, sumber in aktif_tugas:
                lines.append(f"• `[{t_id}]` *{waktu}* — {deskripsi} (via {sumber})")
                
        lines.append("\n*Cara menambah pengingat baru:*")
        lines.append("`/tugas <HH:MM> <deskripsi>` (hari ini)")
        lines.append("`/tugas <YYYY-MM-DD> <HH:MM> <deskripsi>`")
        lines.append("\n*Contoh:*")
        lines.append("`/tugas 15:30 Beli Kopi`")
        lines.append("`/tugas 2026-06-15 15:30 Rapat`")
        lines.append("\n*Menyelesaikan & menghapus pengingat:*")
        lines.append("`/tugas_selesai <id>` — Tandai selesai")
        lines.append("`/tugas_hapus <id>` — Hapus pengingat")
        
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # Parse arguments
    try:
        # Check format: YYYY-MM-DD HH:MM
        if len(args) >= 3 and re.match(r'^\d{4}-\d{2}-\d{2}$', args[0]) and re.match(r'^\d{2}:\d{2}$', args[1]):
            waktu = f"{args[0]} {args[1]}"
            deskripsi = " ".join(args[2:])
        # Check format: HH:MM
        elif len(args) >= 2 and re.match(r'^\d{2}:\d{2}$', args[0]):
            waktu = args[0]
            deskripsi = " ".join(args[1:])
        else:
            await update.message.reply_text(
                "❌ *Format tidak valid!*\n"
                "Gunakan format:\n"
                "• `/tugas <HH:MM> <deskripsi>`\n"
                "• `/tugas <YYYY-MM-DD> <HH:MM> <deskripsi>`",
                parse_mode="Markdown"
            )
            return
            
        if core.tambah_tugas(waktu, deskripsi, "telegram"):
            await update.message.reply_text(
                f"⏰ *Pengingat berhasil disimpan!*\n"
                f"• *Waktu:* {waktu}\n"
                f"• *Deskripsi:* {deskripsi}\n"
                f"Aku akan mengingatkanmu di PC dan Telegram saat waktunya tiba.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Gagal menyimpan pengingat ke database.")
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {e}")

@restricted
async def tugas_selesai_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tugas_selesai <id> command."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Format salah. Gunakan: `/tugas_selesai <id_tugas>`", parse_mode="Markdown")
        return
        
    t_id = int(args[0])
    if core.update_status_tugas(t_id, 'selesai'):
        await update.message.reply_text(f"✓ Pengingat `[{t_id}]` berhasil ditandai selesai.")
    else:
        await update.message.reply_text(f"❌ Gagal memperbarui status pengingat `[{t_id}]`.")

@restricted
async def tugas_hapus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /tugas_hapus <id> command."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Format salah. Gunakan: `/tugas_hapus <id_tugas>`", parse_mode="Markdown")
        return
        
    t_id = int(args[0])
    if core.hapus_tugas(t_id):
        await update.message.reply_text(f"✓ Pengingat `[{t_id}]` berhasil dihapus.")
    else:
        await update.message.reply_text(f"❌ Gagal menghapus pengingat `[{t_id}]`.")

@restricted
async def note_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /note command to list or add notes."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args:
        # Tampilkan daftar catatan
        catatan_list = core.ambil_semua_catatan()
        
        panggilan = core.dapatkan_panggilan_user()
        panggilan_str = f" {panggilan}" if panggilan else ""
        
        lines = [f"📝 *Daftar Catatan Amadeus Untuk{panggilan_str}:*"]
        if not catatan_list:
            lines.append("_Belum ada catatan._")
        else:
            for c_id, tgl, judul, konten, sumber in catatan_list:
                lines.append(f"• `[{c_id}]` *{judul}* ({tgl[:10]})")
                
        lines.append("\n*Cara membuat catatan baru:*")
        lines.append("`/note <judul> | <konten>`")
        lines.append("`/note <konten>` (judul otomatis)")
        lines.append("\n*Membaca & menghapus catatan:*")
        lines.append("`/note_detail <id>` — Baca isi lengkap")
        lines.append("`/note_hapus <id>` — Hapus catatan")
        
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")
        return

    # Parse arguments untuk membuat catatan baru
    raw_args = " ".join(args)
    try:
        if "|" in raw_args:
            judul, konten = raw_args.split("|", 1)
            judul = judul.strip()
            konten = konten.strip()
        else:
            konten = raw_args.strip()
            # Judul otomatis dari 4 kata pertama
            words = konten.split()
            judul = " ".join(words[:4]) + ("..." if len(words) > 4 else "")
            
        if core.tambah_catatan(judul, konten, "telegram"):
            await update.message.reply_text(
                f"📝 *Catatan berhasil disimpan!*\n"
                f"• *Judul:* {judul}\n"
                f"Tersinkronisasi dengan desktop VN Amadeus.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Gagal menyimpan catatan ke database.")
    except Exception as e:
        await update.message.reply_text(f"❌ Terjadi kesalahan: {e}")

@restricted
async def note_detail_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /note_detail <id> command."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Format salah. Gunakan: `/note_detail <id_catatan>`", parse_mode="Markdown")
        return
        
    c_id = int(args[0])
    catatan_list = core.ambil_semua_catatan()
    catatan = next((c for c in catatan_list if c[0] == c_id), None)
    
    if catatan:
        _, tgl, judul, konten, sumber = catatan
        response_text = (
            f"📝 *Detail Catatan [{c_id}]:*\n\n"
            f"📌 *Judul:* {judul}\n"
            f"📅 *Tanggal:* {tgl}\n"
            f"📡 *Sumber:* {sumber.upper()}\n\n"
            f"💬 *Isi Catatan:*\n{konten}"
        )
        await update.message.reply_text(response_text, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ Catatan dengan ID `[{c_id}]` tidak ditemukan.", parse_mode="Markdown")

@restricted
async def note_hapus_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /note_hapus <id> command."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    args = context.args
    if not args or not args[0].isdigit():
        await update.message.reply_text("❌ Format salah. Gunakan: `/note_hapus <id_catatan>`", parse_mode="Markdown")
        return
        
    c_id = int(args[0])
    if core.hapus_catatan(c_id):
        await update.message.reply_text(f"✓ Catatan `[{c_id}]` berhasil dihapus.")
    else:
        await update.message.reply_text(f"❌ Gagal menghapus catatan `[{c_id}]`.")

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display bot commands and help info."""
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    panggilan = core.dapatkan_panggilan_user()
    panggilan_str = f" {panggilan}" if panggilan else ""
    
    help_text = (
        f"📝 *Panduan Asisten Amadeus Untuk{panggilan_str}:*\n\n"
        "*🤖 PERINTAH BOT TELEGRAM:*\n"
        "• `/start` — Mulai sesi obrolan\n"
        "• `/help` — Tampilkan panduan ini\n"
        "• `/settings` — Cek konfigurasi aktif Amadeus\n"
        "• `/model` — Pilih otak AI (Lokal/Gemini)\n"
        "• `/saldo` — Cek saldo keuangan saat ini\n"
        "• `/riwayat` — Lihat 5 transaksi keuangan terbaru\n"
        "• `/memory` — Cek memori Kurisu tentangmu\n"
        "• `/memory <teks>` — Perbarui memori kustom\n"
        "• `/tugas` — Cek daftar pengingat alarm aktif\n"
        "• `/tugas <waktu> <deskripsi>` — Tambah pengingat baru\n"
        "• `/tugas_selesai <id>` — Tandai tugas selesai\n"
        "• `/tugas_hapus <id>` — Hapus pengingat tugas\n"
        "• `/note` — Cek daftar catatan aktif\n"
        "• `/note <judul> | <konten>` — Tambah catatan baru\n"
        "• `/note_detail <id>` — Baca isi detail catatan\n"
        "• `/note_hapus <id>` — Hapus catatan dari database\n\n"
        "*💬 FITUR SINKRONISASI OBROLAN AI:*\n"
        "Kamu juga bisa mengobrol biasa denganku untuk:\n"
        "1. *Mencatat Keuangan*: Kirim pesan seperti `\"Beli ramen Rp 35.000\"`.\n"
        "2. *Mengatur Alarm*: Kirim pesan seperti `\"Ingatkan aku jam 12:00 makan siang\"`.\n"
        "3. *Menulis Catatan*: Kirim pesan seperti `\"Catat ide ini: membuat mesin waktu\"`.\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

@restricted
async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle incoming Telegram voice notes, transcribe them, and chat with Amadeus."""
    if not update.message or not update.message.voice:
        return
        
    # Cache chat ID
    if update.effective_chat:
        save_chat_id(update.effective_chat.id)
        
    # Kirim pesan status sementara
    status_msg = await update.message.reply_text("Amadeus sedang mendengarkan pesan suara Anda... 🎙️")
    
    try:
        import soundfile as sf
        import speech_recognition as sr
    except ImportError:
        await status_msg.edit_text(
            "❌ *Gagal memproses pesan suara!*\n\n"
            "Library pendukung belum lengkap di komputer server.\n"
            "Silakan jalankan perintah ini di terminal server Amadeus:\n"
            "`pip install soundfile SpeechRecognition`",
            parse_mode="Markdown"
        )
        return

    # Buat nama berkas temporer di folder Ignore folder
    temp_dir = os.path.join(core.BASE_DIR, "Ignore folder")
    if not os.path.exists(temp_dir):
        os.makedirs(temp_dir)
        
    ogg_path = os.path.join(temp_dir, f"temp_{update.effective_user.id}.ogg")
    wav_path = os.path.join(temp_dir, f"temp_{update.effective_user.id}.wav")
    
    try:
        # 1. Download file OGG dari Telegram
        voice_file = await update.message.voice.get_file()
        await voice_file.download_to_drive(ogg_path)
        
        # 2. Konversi OGG ke WAV menggunakan soundfile
        try:
            data, samplerate = sf.read(ogg_path)
            sf.write(wav_path, data, samplerate)
        except Exception as e_conv:
            logger.error(f"Gagal mengonversi OGG ke WAV: {e_conv}")
            await status_msg.edit_text(
                "❌ *Gagal membaca format suara!*\n"
                "Format audio OGG/Opus yang dikirim tidak didukung atau rusak.",
                parse_mode="Markdown"
            )
            return
            
        # 3. Transkripsi WAV ke Teks menggunakan SpeechRecognition (Bahasa Indonesia)
        r = sr.Recognizer()
        try:
            with sr.AudioFile(wav_path) as source:
                audio_data = r.record(source)
            recognized_text = r.recognize_google(audio_data, language="id-ID")
            logger.info(f"[VOICE] Hasil transkripsi: '{recognized_text}'")
        except sr.UnknownValueError:
            await status_msg.edit_text("❌ Suara tidak terdengar jelas atau tidak dipahami oleh Amadeus.")
            return
        except sr.RequestError as e_req:
            await status_msg.edit_text(f"❌ Layanan Speech Recognition error: {e_req}")
            return
            
        # 4. Update status pesan transkripsi di chat
        await status_msg.edit_text(f"🗣️ *Anda:* _{recognized_text}_\n\n👩‍🦰 _Memproses balasan..._", parse_mode="Markdown")
        
        # 5. Kirim teks hasil transkripsi ke AI Amadeus
        reply_text, row_id = chat_dengan_amadeus(recognized_text, sumber="telegram", return_id=True)
        
        # Extract mood tag if any
        mood_match = re.search(r'\[([a-zA-Z0-9_\s\-]+)\]', reply_text)
        mood = mood_match.group(1).lower().strip() if mood_match else "normal"
        
        reply_text_clean = re.sub(r'\[.*?\]', '', reply_text).strip()
        
        # Log structured interaction to GUI
        if log_queue is not None:
            log_queue.put({
                "type": "telegram_chat",
                "user_text": recognized_text,
                "reply_text": reply_text_clean,
                "mood": mood,
                "is_voice": True
            })
            
        # 6. Tampilkan balasan akhir dengan keyboard rating
        await status_msg.edit_text(f"🗣️ *Anda:* _{recognized_text}_\n\n *Amadeus:*\n{reply_text_clean}", parse_mode="Markdown", reply_markup=get_rate_keyboard(row_id))

    except Exception as e:
        logger.error(f"Error memproses pesan suara: {e}")
        await status_msg.edit_text(f"❌ Terjadi kesalahan saat memproses audio: {e}")
        
    finally:
        # Bersihkan file sampah temporer
        if os.path.exists(ogg_path):
            try: os.remove(ogg_path)
            except: pass
        if os.path.exists(wav_path):
            try: os.remove(wav_path)
            except: pass

def main() -> None:
    """Start the bot."""
    if not TOKEN:
        print("[ERROR] TELEGRAM_BOT_TOKEN tidak ditemukan di file .env!")
        return

    # Initialize SQLite database structure if not already present
    fungsi_setup_database()
    
    print("[SYSTEM LOG] Memulai bot Telegram Amadeus...")
    
    # Build Telegram App
    application = Application.builder().token(TOKEN).build()

    # Register commands and callback query handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("model", set_model_command))
    application.add_handler(CommandHandler("saldo", saldo_command))
    application.add_handler(CommandHandler("riwayat", riwayat_command))
    application.add_handler(CommandHandler("memory", memory_command))
    application.add_handler(CommandHandler("tugas", tugas_command))
    application.add_handler(CommandHandler("tugas_selesai", tugas_selesai_command))
    application.add_handler(CommandHandler("tugas_hapus", tugas_hapus_command))
    application.add_handler(CommandHandler("note", note_command))
    application.add_handler(CommandHandler("note_detail", note_detail_command))
    application.add_handler(CommandHandler("note_hapus", note_hapus_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Callback query handlers for model selector and rating button clicks
    application.add_handler(CallbackQueryHandler(model_callback_handler, pattern="^(local|cloud_2_5|cloud_3_5)$"))
    application.add_handler(CallbackQueryHandler(rate_callback_handler, pattern="^rate_lora:"))
    
    # General messages
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Voice messages
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))

    # Run the bot polling
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
