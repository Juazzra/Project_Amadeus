from google import genai

import os

# Load environment variables manually from root or Ignore folder
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
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

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=GEMINI_API_KEY)

# Daftar model yang akan kita tes berurutan
daftar_model = [
    'gemini-2.5-flash',
    'gemini-3.5-flash',
]

print("="*50)
print("SISTEM DIAGNOSTIK API AMADEUS")
print("="*50)

for nama_model in daftar_model:
    print(f"\nMenguji model : {nama_model}")
    print("Status        : Sedang mengirim request...")
    
    try:
        # Mengirim prompt sangat ringan
        response = client.models.generate_content(
            model=nama_model,
            contents="Halo, balas dengan kata 'OK' saja."
        )
        print(f"Hasil         : [OK] BERHASIL! (Balasan: {response.text.strip()})")
        
    except Exception as e:
        pesan_error = str(e)
        if "429" in pesan_error or "Quota" in pesan_error:
            print("Hasil         : [FAIL] GAGAL (Kena Limit Kuota / 429 Resource Exhausted)")
        elif "404" in pesan_error:
            print("Hasil         : [FAIL] GAGAL (Model tidak ditemukan / 404 Not Found)")
        else:
            print(f"Hasil         : [FAIL] GAGAL (Error lain: {pesan_error})")

print("\n" + "="*50)
print("DIAGNOSTIK SELESAI")