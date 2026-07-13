import os
from dotenv import load_dotenv
from typing import Final, Dict

# Memuat file .env
load_dotenv()

# --- KREDENSIAL  ---
TOKEN: Final[str] = os.getenv("TELEGRAM_TOKEN", "")
GEMINI_API_KEY: Final[str] = os.getenv("GEMINI_API_KEY", "")

if not TOKEN or not GEMINI_API_KEY:
    missing = []
    if not TOKEN:
        missing.append("TELEGRAM_TOKEN")
    if not GEMINI_API_KEY:
        missing.append("GEMINI_API_KEY")
    raise ValueError(f"ERROR: Kredensial berikut belum diisi di file .env atau environment: {', '.join(missing)}")

# --- PENGATURAN APLIKASI ---
MAX_CHARS: Final[int] = 50000
CHUNK_SIZE: Final[int] = 2500
MAX_WORDS_IN_CHAT: Final[int] = 300
MAX_FILE_SIZE_MB: Final[int] = 20

# --- MAPPING BAHASA UNTUK TTS ---
VOICE_MAPPING: Final[Dict[str, Dict[str, str]]] = {
    'id': {'female': 'id-ID-Standard-A', 'male': 'id-ID-Standard-B'},
    'en': {'female': 'en-US-Standard-C', 'male': 'en-US-Standard-D'},
    'ja': {'female': 'ja-JP-Standard-A', 'male': 'ja-JP-Standard-B'},
    'ko': {'female': 'ko-KR-Standard-A', 'male': 'ko-KR-Standard-C'},
    'ar': {'female': 'ar-XA-Standard-A', 'male': 'ar-XA-Standard-B'}
}