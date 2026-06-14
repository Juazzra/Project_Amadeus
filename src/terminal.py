# Mengimpor fungsi dari file core.py yang baru saja kita buat
from core import chat_dengan_amadeus, fungsi_setup_database

def mulai_sesi():
    # Pastikan database siap setiap kali terminal dijalankan
    fungsi_setup_database()
    
    print("="*50)
    print("Sistem Amadeus (Versi Terminal) - Online")
    print("Ketik 'exit' atau 'keluar' untuk mematikan sistem.")
    print("="*50)
    
    while True:
        # Mengambil input dari pengguna di terminal
        pesan = input("\nKamu: ")
        
        # Logika untuk keluar dari loop/program
        if pesan.lower() in ['exit', 'keluar']:
            print("Amadeus: Sistem mematikan daya. El Psy Kongroo.")
            break
            
        # Jika input kosong, abaikan
        if not pesan.strip():
            continue
            
        # Memproses pesan ke AI
        balasan = chat_dengan_amadeus(pesan)
        print(f"Amadeus: {balasan}")

# Menjalankan aplikasi terminal
if __name__ == "__main__":
    mulai_sesi()