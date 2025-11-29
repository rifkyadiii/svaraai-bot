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
    'id': {'female': 'id-ID-GadisNeural', 'male': 'id-ID-ArdiNeural'},
    'en': {'female': 'en-US-JennyNeural', 'male': 'en-US-ChristopherNeural'},
    'ja': {'female': 'ja-JP-NanamiNeural', 'male': 'ja-JP-KeitaNeural'},
    'ko': {'female': 'ko-KR-SunHiNeural', 'male': 'ko-KR-InJoonNeural'},
    'ar': {'female': 'ar-SA-ZariyahNeural', 'male': 'ar-SA-HamedNeural'}
}