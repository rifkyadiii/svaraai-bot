import logging
import os
import glob
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse, JSONResponse
from contextlib import asynccontextmanager
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, filters
from telegram.request import HTTPXRequest

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

# --- KONFIGURASI REQUEST ---
t_request = HTTPXRequest(
    connection_pool_size=8,
    read_timeout=600.0,
    write_timeout=600.0,
    connect_timeout=60.0
)

# --- SETUP BOT TELEGRAM ---
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

WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Membersihkan file sampah (.mp3 & .txt)...")
    for file in glob.glob("/tmp/*.mp3"):
        try: os.remove(file)
        except: pass
    for file in glob.glob("/tmp/*.txt"):
        if "requirements.txt" not in file:
            try: os.remove(file)
            except: pass

    logger.info("Server Start: Telegram Bot (webhook mode) + REST API")
    await bot_app.initialize()
    await bot_app.start()

    yield

    logger.info("Server Stop")
    await bot_app.stop()
    await bot_app.shutdown()


app = FastAPI(
    title="SvaraAI Bot API",
    description="""
                API dari SvaraAI Bot dengan endpoint sebagai berikut:
                1. OCR: Ekstraksi teks dari gambar menggunakan model AI Gemini.
                2. File Extractor: Pengambilan konten dari dokumen (PDF, DOCX, TXT).
                3. Summarizer: Peringkasan teks menggunakan model AI Gemini.
                4. Translator: Layanan terjemahan bahasa.
                5. TTS: Konversi Teks-ke-Suara menggunakan EdgeTTS.
                """,
    version="1.0",
    lifespan=lifespan
)
app.include_router(api.routes.router)


@app.get("/", include_in_schema=False)
async def index():
    return RedirectResponse(url="/docs")


@app.post("/telegram-webhook")
async def telegram_webhook(request: Request):
    if WEBHOOK_SECRET:
        header_token = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if header_token != WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid secret token")

    data = await request.json()
    update = Update.de_json(data, bot_app.bot)
    await bot_app.process_update(update)
    return JSONResponse({"ok": True})


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)