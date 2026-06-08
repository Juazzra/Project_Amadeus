from google import genai

import os

# Load environment variables manually from Ignore folder/.env
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env_path = os.path.join(BASE_DIR, "Ignore folder", ".env")
if os.path.exists(env_path):
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                if "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip().strip('"').strip("'")

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

print("Mencari model yang tersedia untuk akun ini...")
try:
    for m in client.models.list():
        # Memfilter agar hanya menampilkan model yang mendukung generateContent
        if 'generateContent' in m.supported_actions:
            print(f"✅ {m.name}")
except Exception as e:
    print(f"Gagal mengambil daftar model: {e}")