import os
import google.generativeai as genai
from PIL import Image
import io
import edge_tts
import PyPDF2
import docx
import config

# --- SETUP GOOGLE GEMINI ---
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

LANG_NAMES = {
    'id': 'Indonesian', 'en': 'English', 'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic'
}

# --- 1. OCR ---
def ocr_with_gemini(image_bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        prompt = "Extract all text from this image exactly as it appears. Do not summarize yet."
        response = model.generate_content([prompt, image])
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error Gemini OCR: {e}")
        return None

# --- 2. SUMMARIZER ---
def summarize_text(text: str) -> str:
    """
    Meringkas teks menjadi PARAGRAF NARASI yang PADAT & SINGKAT.
    """
    try:
        # Prompt Baru: Fokus pada efisiensi kata
        prompt = (
            "You are a professional editor. Your goal is to summarize the text concisely. "
            "1. The summary MUST be significantly shorter than the original text. "
            "2. Do NOT use introductory phrases like 'Here is the summary', 'Halo pendengar', or 'Berikut ringkasannya'. "
            "3. Start directly with the main content. "
            "4. Combine main ideas into flowing paragraphs. "
            "5. Do NOT use bullet points. "
            "6. Respond in the same language as the original text.\n\n"
            f"TEXT TO SUMMARIZE:\n{text[:config.MAX_CHARS]}"
        )
        
        response = model.generate_content(prompt)
        
        if not response.text:
            return "⚠️ AI tidak menghasilkan output."
            
        # Cleaning Manual
        clean_text = response.text.strip()
        clean_text = clean_text.replace("* ", "").replace("- ", "").replace("• ", "").replace("**", "")
        
        return clean_text

    except Exception as e:
        return f"⚠️ Gagal Meringkas. Error API: {str(e)}"

# --- 3. TRANSLATOR ---
def translate_text(text: str, target_lang_code: str) -> str:
    try:
        target_lang_name = LANG_NAMES.get(target_lang_code, 'English')
        prompt = (
            f"Translate the following text into natural, native-sounding {target_lang_name}. "
            "STRICT RULES:\n"
            f"1. If the text is ALREADY in {target_lang_name}, RETURN IT EXACTLY AS IS. DO NOT PARAPHRASE. DO NOT CHANGE A SINGLE WORD.\n"
            "2. If it is in a different language, translate it accurately.\n"
            "3. Do not add any introductory phrases. "
            "4. Do not add explanations. "
            "Just output the translation directly.\n\n"
            f"TEXT:\n{text[:config.MAX_CHARS]}"
        )
        response = model.generate_content(prompt)
        if not response.text: return text
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error Translate: {e}")
        return text 

# --- 4. TTS GENERATOR (SMART CHUNKING) ---

# Helper: Memecah teks besar menjadi list potongan kalimat
def split_text_smartly(text, limit):
    chunks = []
    current_chunk = ""
    # Pecah berdasarkan kalimat (titik) biar natural
    sentences = text.replace('\n', ' ').split('. ') 
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < limit:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

# Fungsi Utama TTS dengan Progress Callback
async def generate_audio_long(text: str, lang: str, gender: str, user_id: str, progress_callback=None) -> str:
    try:
        voice_dict = config.VOICE_MAPPING.get(lang, config.VOICE_MAPPING['en'])
        selected_voice = voice_dict.get(gender, voice_dict['female'])
        
        # 1. Pecah Teks
        chunks = split_text_smartly(text, config.CHUNK_SIZE)
        total_chunks = len(chunks)
        temp_files = []

        # 2. Proses per Chunk
        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            # Update Progress Bar di Telegram (jika ada callback)
            if progress_callback:
                await progress_callback(i + 1, total_chunks)

            temp_file = f"temp_{user_id}_part{i}.mp3"
            communicate = edge_tts.Communicate(chunk, selected_voice)
            await communicate.save(temp_file)
            temp_files.append(temp_file)

        # 3. Dirty Merge (Penggabungan Biner Cepat)
        final_filename = f"audio_{user_id}_final.mp3"
        with open(final_filename, 'wb') as outfile:
            for f_path in temp_files:
                if os.path.exists(f_path):
                    with open(f_path, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(f_path) # Hapus part setelah digabung

        return final_filename

    except Exception as e:
        print(f"❌ Error TTS Long: {e}")
        return None

# --- 5. FILE EXTRACTOR ---
def extract_document_content(file_path: str) -> str:
    text = ""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    t = page.extract_text()
                    if t: text += t + "\n"
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            for para in doc.paragraphs: text += para.text + "\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs: text += para.text + "\n"
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f: text = f.read()
    except Exception as e:
        print(f"❌ Error Read File: {e}")
        return None
    return text.strip()