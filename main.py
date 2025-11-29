import logging
import os
import uvicorn
import glob
from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from contextlib import asynccontextmanager
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest  # <--- IMPORT PENTING

# Import Modul
import config
import handlers
import api.routes

# --- SETUP LOGGING ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- KONFIGURASI REQUEST (AGAR TIDAK TIMEOUT) ---
# Kita set timeout jadi 600 detik (10 menit) untuk jaga-jaga file besar
t_request = HTTPXRequest(
    connection_pool_size=8,
    read_timeout=600.0,  # Waktu tunggu respon Telegram
    write_timeout=600.0, # Waktu tunggu UPLOAD file (Penting!)
    connect_timeout=60.0
)

# --- SETUP BOT TELEGRAM ---
# Masukkan request=t_request ke dalam builder
bot_app = ApplicationBuilder().token(config.TOKEN).request(t_request).build()

# Register Command
bot_app.add_handler(CommandHandler("start", handlers.start))
bot_app.add_handler(CommandHandler("summarize", handlers.cmd_summarize))
bot_app.add_handler(CommandHandler("translate", handlers.cmd_translate))
bot_app.add_handler(CommandHandler("stop", handlers.cmd_stop))

bot_app.add_error_handler(handlers.error_handler)
input_filter = (filters.PHOTO) | (filters.Document.ALL) | (filters.TEXT & ~filters.COMMAND)
bot_app.add_handler(MessageHandler(input_filter, handlers.handle_input))
bot_app.add_handler(CallbackQueryHandler(handlers.callback_handler))

# --- SETUP FASTAPI ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- TAMBAHAN 2: BERSIH-BERSIH SAAT STARTUP ---
    logger.info("Membersihkan file sampah (.mp3 & .txt)...")
    for file in glob.glob("*.mp3"):
        try: os.remove(file)
        except: pass
    for file in glob.glob("*.txt"): # Hapus sisa txt juga
        if "requirements.txt" not in file: # Jangan hapus requirements!
            try: os.remove(file)
            except: pass
    
    logger.info("Server Start: Telegram Bot + REST API")
    await bot_app.initialize()
    await bot_app.start()
    
    await bot_app.updater.start_polling(allowed_updates=["message", "callback_query"])
    
    yield
    
    logger.info("Server Stop")
    await bot_app.updater.stop()
    await bot_app.stop()
    await bot_app.shutdown()

app = FastAPI(
    title="SvuaraAI Bot API",
    description="""
                API dari SvuaraAI Bot dengan endpoint sebagai berikut:
                1. OCR (Optical Character Recognition): Ekstraksi teks dari gambar menjadi text menggunakan model AI Gemini.
                2. File Extractor: Pengambilan konten dari dokumen (PDF, DOCX, TXT).
                3. Summarizer: Peringkasan teks menggunakan model AI Gemini.
                4. Translator: Layanan terjemahan bahasa.
                5. TTS: Konversi Teks-ke-Suara (Text-to-Speech) menggunakan EdgeTTS.
                """,
    version="1.0",
    lifespan=lifespan
)

app.include_router(api.routes.router)

@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse(url="/docs")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)