import sys
import os

# Add src to python path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))

import core

# Set mode to Gemini 2.5
core.set_mode_ai("cloud_2_5")

print("MODE_AI_AKTIF =", core.MODE_AI_AKTIF)
print("GEMINI_API_KEY =", len(core.GEMINI_API_KEY) if core.GEMINI_API_KEY else 0, "chars")

# Call chat_dengan_amadeus
print("Sending test message to Gemini...")
reply = core.chat_dengan_amadeus("Halo Kurisu, apakah kamu di sana?")
print("Reply received:")
print(reply)
