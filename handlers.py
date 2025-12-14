import os
import asyncio
import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ChatAction
import config
import services

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. LOADING BAR HELPER
# ==============================================================================

async def processing_with_bar(context, message, prefix_text, task_function, *args):
    loop = asyncio.get_running_loop()
    future = loop.run_in_executor(None, task_function, *args)
    percent = 0
    while not future.done():
        if percent < 90:
            increment = random.randint(5, 15)
            percent = min(percent + increment, 90)
        bar_len = 10
        filled = int((percent / 100) * bar_len)
        bar = "█" * filled + "░" * (bar_len - filled)
        try:
            await message.edit_text(f"{prefix_text}\n`[{bar}] {percent}%`", parse_mode='Markdown')
        except: pass
        await asyncio.sleep(1.5)
    result = await future
    try:
        await message.edit_text(f"{prefix_text}\n`[██████████] 100%`", parse_mode='Markdown')
        await asyncio.sleep(0.5)
        await message.delete() 
    except: pass
    return result

# ==============================================================================
# 2. KEYBOARD MANAGERS
# ==============================================================================

def get_main_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Mode Meringkas Teks (/summarize)", callback_data='mode_summarize')],
        [InlineKeyboardButton("🌐 Mode Menerjemahkan Teks (/translate)", callback_data='mode_translate')],
        [InlineKeyboardButton("🛑 Hentikan Bot (/stop)", callback_data='stop_bot')]
    ])

def create_lang_kb(data_id, mode_prefix):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🇰🇷 Korea", callback_data=f'lang_ko_{mode_prefix}_{data_id}'),
         InlineKeyboardButton("🇺🇸 Inggris", callback_data=f'lang_en_{mode_prefix}_{data_id}')],
        [InlineKeyboardButton("🇸🇦 Arab", callback_data=f'lang_ar_{mode_prefix}_{data_id}'),
         InlineKeyboardButton("🇯🇵 Jepang", callback_data=f'lang_ja_{mode_prefix}_{data_id}')],
        [InlineKeyboardButton("🇮🇩 Indonesia", callback_data=f'lang_id_{mode_prefix}_{data_id}')]
    ])

def create_post_summary_kb(data_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📝 Terjemahkan Teks", callback_data=f'deep_trans_{data_id}'),
        InlineKeyboardButton("🔙 Selesai (Menu Utama)", callback_data='done')],
        [InlineKeyboardButton("🗣️ Baca Suara (TTS)", callback_data=f'setmode_tts_{data_id}')]
    ])

def create_post_translate_kb(data_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🧠 Rangkum Teks", callback_data=f'deep_sum_{data_id}'),
        InlineKeyboardButton("🔙 Selesai (Menu Utama)", callback_data='done')],
        [InlineKeyboardButton("🗣️ Baca Suara (TTS)", callback_data=f'setmode_tts_{data_id}')]
    ])

def create_terminal_kb(data_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🗣️ Baca Suara (TTS)", callback_data=f'setmode_tts_{data_id}')],
        [InlineKeyboardButton("🔙 Selesai (Menu Utama)", callback_data='done')]
    ])

def create_finish_kb(data_id):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Bahasa Lain", callback_data=f'retry_tts_{data_id}')],
        [InlineKeyboardButton("🔙 Selesai (Menu Utama)", callback_data='done')]
    ])

# ==============================================================================
# 3. HELPER UTILS
# ==============================================================================

async def send_text_result(message, text, title=""):
    w_count = len(text.split())
    stats = f"{w_count} kata"
    if title:
        await message.reply_text(f"📝 **{title}** | {stats}:", parse_mode='Markdown')
    if w_count > config.MAX_WORDS_IN_CHAT:
        fname = "hasil_teks.txt"
        with open(fname, 'w', encoding='utf-8') as f: f.write(text)
        await message.reply_document(open(fname, 'rb'), caption=f"📄 Isi Teks Lengkap {stats}")
        try: os.remove(fname)
        except: pass
    else:
        await message.reply_text(text)

async def show_main_menu(message, text=""):
    msg = text if text else "🤖 **Menu Utama SvaraAI**\nSilakan pilih mode atau kirim file:"
    await message.reply_text(msg, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')
    
def get_language_name(lang_code):
    """Mengembalikan nama bahasa lengkap."""
    lang_map = {
        'ko': 'Korea',
        'en': 'Inggris',
        'ar': 'Arab',
        'ja': 'Jepang',
        'id': 'Indonesia'
    }
    return lang_map.get(lang_code.lower(), lang_code.title())

# ==============================================================================
# 4. HANDLERS COMMAND & MODE
# ==============================================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'auto'
    await show_main_menu(update.message, "🤖 **Halo! SvaraAI Siap Membantu.**\nKirim file/foto/teks atau pilih Mode:")

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE, mode: str):
    context.user_data['mode'] = mode
    mode_text = {
        'summarize': "🧠 **Mode Meringkas Aktif**\n\nKirim Teks -> Langsung Meringkas.",
        'translate': "🌐 **Mode Menerjemahkan Aktif**\n\nKirim Teks -> Langsung Menerjemahkan.",
    }
    msg = f"{mode_text.get(mode, 'Mode Aktif')}\n🚀 Silakan kirim **Foto, File, atau Teks**!"
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown')
    else:
        await update.message.reply_text(msg, parse_mode='Markdown')

async def cmd_summarize(u, c): await set_mode(u, c, 'summarize')
async def cmd_translate(u, c): await set_mode(u, c, 'translate')
async def cmd_tts(u, c): await set_mode(u, c, 'auto')
async def cmd_stop(u, c):
    c.user_data.clear()
    await u.message.reply_text("🛑 Bot Dihentikan. Ketik /start untuk mulai.")

# ==============================================================================
# 5. INPUT PROCESSING
# ==============================================================================

async def handle_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    msg_id = update.message.message_id
    text_result = ""
    current_mode = context.user_data.get('mode', 'auto')

    if update.message.photo:
        photo = update.message.photo[-1]
        if (photo.file_size/1024/1024) > config.MAX_FILE_SIZE_MB:
            await update.message.reply_text("❌ Foto terlalu besar."); return
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.TYPING)
        file = await photo.get_file()
        bytes_data = await file.download_as_bytearray()
        status = await update.message.reply_text("⏳ **Memindai Gambar (OCR)**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
        text_result = await processing_with_bar(context, status, "⏳ **Memindai Gambar (OCR)**", services.ocr_with_gemini, bytes_data)

    elif update.message.document:
        doc = update.message.document
        ext = os.path.splitext(doc.file_name)[1].lower()
        if ext not in ['.pdf', '.docx', '.txt']: await update.message.reply_text("❌ Format salah."); return
        status = await update.message.reply_text("⏳ **Membaca Dokumen**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
        f = await doc.get_file()
        path = f"temp_{doc.file_unique_id}{ext}"
        await f.download_to_drive(path)
        text_result = await processing_with_bar(context, status, "⏳ **Membaca Dokumen**", services.extract_document_content, path)
        if os.path.exists(path): os.remove(path)

    elif update.message.text:
        text_result = update.message.text

    if text_result:
        if len(text_result) > config.MAX_CHARS:
             await update.message.reply_text(f"❌ Teks kepanjangan (Max {config.MAX_CHARS})."); return

        context.user_data[f'text_{msg_id}'] = text_result
        w_count = len(text_result.split())
        c_count = len(text_result)
        stats = f"{w_count} kata"
        await update.message.reply_text(f"📊 **Input Diterima** | {stats}", parse_mode='Markdown')

        if current_mode == 'summarize':
            await execute_summarize(update, context, msg_id, text_result)
        elif current_mode == 'translate':
            await update.message.reply_text("🌐 Pilih Bahasa Terjemahan:", reply_markup=create_lang_kb(msg_id, 'trans'))
        else:
            
            if w_count > 200:
                kb = [[InlineKeyboardButton("🧠 Rangkum Teks", callback_data=f'sum_{msg_id}'),
                       InlineKeyboardButton("📖 Baca Full Teks", callback_data=f'setmode_tts_{msg_id}')]]
                await update.message.reply_text("Mau diproses apa?", reply_markup=InlineKeyboardMarkup(kb))
            else:
                await update.message.reply_text("Pilih Bahasa Audio:", reply_markup=create_lang_kb(msg_id, 'tts'))

# ==============================================================================
# 6. EXECUTION LOGIC (DENGAN MODE CHECK)
# ==============================================================================

async def execute_summarize(update_obj, context, data_id, raw_text, is_final=False):
    message = update_obj.message if update_obj.message else update_obj.callback_query.message
    status = await message.reply_text("⏳ **Sedang Meringkas...**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
    summary = await processing_with_bar(context, status, "⏳ **Sedang Meringkas...**", services.summarize_text, raw_text)
    
    if summary.startswith("⚠️"): await message.reply_text(summary); return

    context.user_data[f'text_{data_id}'] = summary 
    await send_text_result(message, summary, "Hasil Ringkasan")
    
    current_mode = context.user_data.get('mode', 'auto')
    
    if current_mode == 'auto':
        await message.reply_text("🗣️ Pilih Bahasa untuk Membaca Ringkasan:", reply_markup=create_lang_kb(data_id, 'tts'))
    else:
        if is_final:
            await message.reply_text("Opsi Terakhir:", reply_markup=create_terminal_kb(data_id))
        else:
            await message.reply_text("Opsi Lanjutan:", reply_markup=create_post_summary_kb(data_id))

async def execute_translate_only(update_obj, context, data_id, lang_code, is_final=False):
    message = update_obj.message if update_obj.message else update_obj.callback_query.message
    text_source = context.user_data.get(f'text_{data_id}')
    if not text_source: await message.reply_text("⚠️ Data expired."); return
    
    lang_name = get_language_name(lang_code)

    status = await message.reply_text(f"📝 **Menerjemahkan ke Bahasa {lang_name}**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
    final_text = await processing_with_bar(context, status, f"📝 **Menerjemahkan ke Bahasa {lang_name}**", services.translate_text, text_source, lang_code)
    
    context.user_data[f'text_{data_id}'] = final_text 
    await send_text_result(message, final_text, f"Hasil Terjemahan Bahasa {lang_name}")
    
    current_mode = context.user_data.get('mode', 'auto')
    
    if current_mode == 'auto':
        kb = [[InlineKeyboardButton("🗣️ Jadikan Suara (TTS)", callback_data=f'setmode_tts_{data_id}')],
              [InlineKeyboardButton("🔙 Selesai (Menu Utama)", callback_data='done')]]
        await message.reply_text("Lanjut jadikan suara?", reply_markup=InlineKeyboardMarkup(kb))
    else:
        # Jika mode COMMAND: Tawarkan Opsi
        if is_final:
            await message.reply_text("Opsi Terakhir:", reply_markup=create_terminal_kb(data_id))
        else:
            await message.reply_text("Opsi Lanjutan:", reply_markup=create_post_translate_kb(data_id))

# ==============================================================================
# 7. CALLBACK HANDLER
# ==============================================================================

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    
    if data == 'stop_bot':
        context.user_data.clear()
        try: await query.message.delete()
        except: pass
        
        await query.message.reply_text("🛑 Bot Dihentikan. Ketik /start untuk mulai.")
        return

    if data == 'done':
        context.user_data.clear()
        context.user_data['mode'] = 'auto'
        try: await query.message.delete()
        except: pass
        
        await show_main_menu(query.message, "✅ **Sesi Selesai.**\nSilakan mulai lagi:")
        return

    if data.startswith('mode_'):
        await set_mode(update, context, data.split('_')[1])
        return

    # CROSS NAVIGATION
    if data.startswith('deep_trans_'):
        data_id = data.split('_')[2]
        await query.message.reply_text("🌐 Pilih Bahasa:", reply_markup=create_lang_kb(data_id, 'transfinal'))
        return

    if data.startswith('deep_sum_'):
        data_id = data.split('_')[2]
        raw_text = context.user_data.get(f'text_{data_id}')
        if not raw_text: await query.edit_message_text("⚠️ Data Expired."); return
        await execute_summarize(update, context, data_id, raw_text, is_final=True)
        return

    if data.startswith('setmode_'):
        parts = data.split('_')
        new_mode = parts[1] 
        data_id = parts[2]
        flag = 'trans' if new_mode == 'translate' else 'tts'
        prompt = "Pilih Bahasa Terjemahan:" if flag == 'trans' else "Pilih Bahasa Audio:"
        await query.message.reply_text(prompt, reply_markup=create_lang_kb(data_id, flag))
        return

    if data.startswith('retry_tts_'):
        data_id = data.split('_')[2]
        await query.message.reply_text("Pilih Bahasa Audio:", reply_markup=create_lang_kb(data_id, 'tts'))
        return

    parts = data.split('_')
    action = parts[0]

    if action == 'sum':
        data_id = parts[1]
        raw = context.user_data.get(f'text_{data_id}')
        if not raw: await query.edit_message_text("⚠️ Data Expired."); return
        await execute_summarize(update, context, data_id, raw, is_final=False)

    elif action == 'lang':
        lang_code = parts[1]
        mode_flag = parts[2]
        data_id = parts[3]
        
        lang_name = get_language_name(lang_code)
        
        if mode_flag == 'trans':
            await execute_translate_only(update, context, data_id, lang_code, is_final=False)
            return
        if mode_flag == 'transfinal':
            await execute_translate_only(update, context, data_id, lang_code, is_final=True)
            return
            
        kb = [[InlineKeyboardButton("👩 Wanita", callback_data=f'proc_{lang_code}_{mode_flag}_female_{data_id}'),
               InlineKeyboardButton("👨 Pria", callback_data=f'proc_{lang_code}_{mode_flag}_male_{data_id}')]]
        await query.edit_message_text(f"Pilih Suara ({lang_name}):", reply_markup=InlineKeyboardMarkup(kb))

    elif action == 'proc':
        lang = parts[1]
        mode_flag = parts[2]
        gender = parts[3]
        data_id = parts[4]
        
        lang_name = get_language_name(lang)
        
        text_source = context.user_data.get(f'text_{data_id}')
        if not text_source: await query.edit_message_text("⚠️ Expired."); return

        status_trans = await query.edit_message_text(f"📝 **Menerjemahkan Audio ke Bahasa {lang_name}**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
        final_text = await processing_with_bar(context, status_trans, f"📝 **Menerjemahkan Audio ke Bahasa {lang_name}**", services.translate_text, text_source, lang)
        
        status_audio = await query.message.reply_text(f"⏳ **Memproses Audio  Bahasa {lang_name}**\n`[░░░░░░░░░░] 0%`", parse_mode='Markdown')
        
        async def progress_cb(cur, tot):
            if cur%2==0 or cur==tot:
                try: 
                    pct = int((cur/tot)*100)
                    bar = "█"*int(pct/10) + "░"*(10-int(pct/10))
                    await status_audio.edit_text(f"⏳ **Memproses Audio Bahasa {lang_name}**\n`[{bar}] {pct}%`", parse_mode='Markdown')
                except: pass

        try:
            audio_path = await services.generate_audio_long(
                final_text, lang, gender, f"{query.from_user.id}_{data_id}", progress_cb
            )
            if not audio_path: await query.message.reply_text("❌ Gagal Audio."); return
            
            await status_audio.delete()
            w_count = len(final_text.split())
            await query.message.reply_audio(
                audio=open(audio_path, 'rb'), 
                caption=f"🎧 Audio: {lang_name} | {gender.title()}\n📊 {w_count} kata"
            )
            
            if final_text.strip() != text_source.strip():
                await send_text_result(query.message, final_text, f"Teks Audio Bahasa {lang_name}")

            if os.path.exists(audio_path): os.remove(audio_path)
            await query.message.reply_text("Selesai.", reply_markup=create_finish_kb(data_id))

        except Exception as e:
            await query.message.reply_text(f"Error: {e}")

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"Error: {context.error}")
    try:
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(f"🔥 Error: {context.error}")
    except: pass