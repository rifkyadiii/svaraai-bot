import os
import re
import asyncio
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

# Flag Error Internal (Tanpa Emoji)
INTERNAL_ERROR_FLAG = "INTERNAL_ERROR: "

# --- HELPER: PEMBERSIH FORMAT TEKS (FIX BUG FORMAT .TXT) ---
def clean_text_formatting(text: str) -> str:
    """
    Membersihkan teks dari enter berlebih yang bikin format file txt aneh.
    Mengubah single newline menjadi spasi, tapi menjaga paragraf (double newline).
    """
    if not text: return ""
    
    # 1. Normalisasi newline (3+ enter jadi 2 enter)
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 2. Perbaiki kalimat terputus (satu kata per baris)
    lines = text.split('\n')
    cleaned_lines = []
    
    for line in lines:
        line = line.strip()
        if not line:
            cleaned_lines.append("") # Jaga jarak paragraf
        else:
            cleaned_lines.append(line)
            
    # Gabung ulang
    text = "\n".join(cleaned_lines)
    
    # Hapus spasi ganda
    text = re.sub(r'[ \t]+', ' ', text)
    
    return text.strip()

# --- 1. OCR DENGAN GEMINI ---
def ocr_with_gemini(image_bytes) -> str:
    try:
        image = Image.open(io.BytesIO(image_bytes))
        prompt = "Extract all text from this image exactly as it appears. Do not summarize yet."
        response = model.generate_content([prompt, image])
        return clean_text_formatting(response.text)
    except Exception as e:
        print(f"Error Gemini OCR: {e}")
        return f"{INTERNAL_ERROR_FLAG}Gagal Baca Gambar: {str(e)}"

# --- 2. SUMMARIZER ---
def summarize_text(text: str) -> str:
    """
    Meringkas teks menjadi PARAGRAF NARASI yang PADAT & SINGKAT.
    """
    try:
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
            return f"{INTERNAL_ERROR_FLAG}AI tidak menghasilkan output."
            
        # Cleaning Manual Simbol List
        clean_text = response.text.strip()
        clean_text = clean_text.replace("* ", "").replace("- ", "").replace("• ", "").replace("**", "")
        
        return clean_text_formatting(clean_text)

    except Exception as e:
        return f"{INTERNAL_ERROR_FLAG}Gagal Meringkas: {str(e)}"

# --- 3. TRANSLATOR ---
def translate_text(text: str, target_lang_code: str) -> str:
    try:
        # Cek error flag dari proses sebelumnya
        if text.startswith(INTERNAL_ERROR_FLAG):
            return text

        target_lang_name = LANG_NAMES.get(target_lang_code, 'English')
        prompt = (
            f"Translate the following text into natural, native-sounding {target_lang_name}. "
            "STRICT RULES:\n"
            f"1. If the text is ALREADY in {target_lang_name}, RETURN IT EXACTLY AS IS. DO NOT PARAPHRASE. DO NOT CHANGE A SINGLE WORD.\n"
            "2. If it is in a different language, translate it accurately.\n"
            "3. Do not add any introductory phrases.\n"
            "4. Do not add explanations.\n"
            "Just output the translation directly.\n\n"
            f"TEXT:\n{text[:config.MAX_CHARS]}"
        )
        response = model.generate_content(prompt)
        if not response.text: return text
        return clean_text_formatting(response.text)
    except Exception as e:
        print(f"Error Translate: {e}")
        return f"{INTERNAL_ERROR_FLAG}Gagal Translate: {str(e)}"

# --- 4. TTS GENERATOR (SMART CHUNKING + RETRY) ---

def split_text_smartly(text, limit):
    chunks = []
    current_chunk = ""
    # Bersihkan karakter yang bisa bikin TTS error
    text = text.replace('"', '').replace("'", "").replace("’", "")
    text = " ".join(text.split()) # Normalisasi spasi
    
    sentences = text.replace('Dr.', 'Dr').replace('Mr.', 'Mr').split('. ') 
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < limit:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

async def generate_audio_long(text: str, lang: str, gender: str, user_id: str, progress_callback=None) -> str:
    try:
        if text.startswith(INTERNAL_ERROR_FLAG):
            return None

        voice_dict = config.VOICE_MAPPING.get(lang, config.VOICE_MAPPING['en'])
        selected_voice = voice_dict.get(gender, voice_dict['female'])
        
        chunks = split_text_smartly(text, config.CHUNK_SIZE)
        total_chunks = len(chunks)
        temp_files = []

        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            
            if progress_callback:
                await progress_callback(i + 1, total_chunks)

            temp_file = f"temp_{user_id}_part{i}.mp3"
            
            # --- RETRY LOGIC (3x Percobaan) ---
            # Ini solusi untuk error "No audio received" di Render
            success = False
            for attempt in range(3):
                try:
                    communicate = edge_tts.Communicate(chunk, selected_voice)
                    await communicate.save(temp_file)
                    success = True
                    break # Berhasil, keluar loop retry
                except Exception as e:
                    print(f"TTS Retry {attempt+1}/3: {e}")
                    await asyncio.sleep(2) # Tunggu 2 detik sebelum coba lagi
            
            if not success:
                # Jika 3x gagal, batalkan semua
                return None

            temp_files.append(temp_file)

        # Dirty Merge (Gabung File)
        final_filename = f"audio_{user_id}_final.mp3"
        with open(final_filename, 'wb') as outfile:
            for f_path in temp_files:
                if os.path.exists(f_path):
                    with open(f_path, 'rb') as infile:
                        outfile.write(infile.read())
                    os.remove(f_path) 
        return final_filename

    except Exception as e:
        print(f"Error TTS Long: {e}")
        return None

# --- 5. FILE EXTRACTOR ---
def extract_document_content(file_path: str) -> str:
    text = ""
    try:
        if file_path.endswith('.pdf'):
            with open(file_path, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    extract = page.extract_text()
                    if extract: text += extract + " " # Pakai spasi
        elif file_path.endswith('.docx'):
            doc = docx.Document(file_path)
            for para in doc.paragraphs: text += para.text + "\n\n"
            for table in doc.tables:
                for row in table.rows:
                    for cell in row.cells:
                        for para in cell.paragraphs: text += para.text + " "
        elif file_path.endswith('.txt'):
            with open(file_path, 'r', encoding='utf-8') as f: text = f.read()
    except Exception as e:
        print(f"Error Read File: {e}")
        return f"{INTERNAL_ERROR_FLAG}Gagal Baca File: {str(e)}"
    
    return clean_text_formatting(text)