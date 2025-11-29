import os
import re
import asyncio
import subprocess  # <--- IMPORT PENTING
import google.generativeai as genai
from PIL import Image
import io
import PyPDF2
import docx
import config

# --- SETUP GOOGLE GEMINI ---
genai.configure(api_key=config.GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

LANG_NAMES = {
    'id': 'Indonesian', 'en': 'English', 'ja': 'Japanese', 'ko': 'Korean', 'ar': 'Arabic'
}

INTERNAL_ERROR_FLAG = "INTERNAL_ERROR: "

# --- HELPER CLEANER ---
def clean_text_formatting(text: str) -> str:
    if not text: return ""
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        line = line.strip()
        if not line: cleaned_lines.append("") 
        else: cleaned_lines.append(line)
    text = "\n".join(cleaned_lines)
    text = re.sub(r'[ \t]+', ' ', text)
    return text.strip()

# --- 1. OCR ---
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
    try:
        prompt = (
            "You are a professional editor. Summarize the text concisely. "
            "Do NOT use intro phrases. Start directly. No bullet points. "
            f"TEXT:\n{text[:config.MAX_CHARS]}"
        )
        response = model.generate_content(prompt)
        if not response.text: return f"{INTERNAL_ERROR_FLAG}AI Error."
        
        clean = response.text.strip().replace("* ", "").replace("- ", "")
        return clean_text_formatting(clean)
    except Exception as e:
        return f"{INTERNAL_ERROR_FLAG}Gagal Ringkas: {str(e)}"

# --- 3. TRANSLATOR ---
def translate_text(text: str, target_lang_code: str) -> str:
    try:
        if text.startswith(INTERNAL_ERROR_FLAG): return text
        target_lang_name = LANG_NAMES.get(target_lang_code, 'English')
        prompt = (
            f"Translate to natural {target_lang_name}. "
            f"If text is already {target_lang_name}, RETURN AS IS. "
            f"TEXT:\n{text[:config.MAX_CHARS]}"
        )
        response = model.generate_content(prompt)
        if not response.text: return text
        return clean_text_formatting(response.text)
    except Exception as e:
        return f"{INTERNAL_ERROR_FLAG}Gagal Translate: {str(e)}"

# --- 4. TTS GENERATOR (SUBPROCESS METHOD - RENDER FIX) ---

def split_text_smartly(text, limit):
    chunks = []
    current_chunk = ""
    text = text.replace('"', '').replace("'", "").replace("`", "") # Hapus quote biar command line aman
    text = " ".join(text.split())
    sentences = text.replace('Dr.', 'Dr').split('. ') 
    
    for sentence in sentences:
        if len(current_chunk) + len(sentence) < limit:
            current_chunk += sentence + ". "
        else:
            chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    if current_chunk:
        chunks.append(current_chunk.strip())
    return chunks

async def run_edge_tts_command(text, voice, output_file):
    """Menjalankan edge-tts lewat terminal (Subprocess)"""
    try:
        # Kita panggil library edge-tts lewat command line
        # Ini menghindari konflik asyncio di dalam Python
        process = await asyncio.create_subprocess_exec(
            "edge-tts",
            "--text", text,
            "--voice", voice,
            "--write-media", output_file,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            print(f"TTS CMD Error: {stderr.decode()}")
            return False
        return True
    except Exception as e:
        print(f"Subprocess Exception: {e}")
        return False

async def generate_audio_long(text: str, lang: str, gender: str, user_id: str, progress_callback=None) -> str:
    try:
        if text.startswith(INTERNAL_ERROR_FLAG): return None

        voice_dict = config.VOICE_MAPPING.get(lang, config.VOICE_MAPPING['en'])
        selected_voice = voice_dict.get(gender, voice_dict['female'])
        
        chunks = split_text_smartly(text, config.CHUNK_SIZE)
        total_chunks = len(chunks)
        temp_files = []

        for i, chunk in enumerate(chunks):
            if not chunk.strip(): continue
            if progress_callback: await progress_callback(i + 1, total_chunks)

            temp_file = f"temp_{user_id}_part{i}.mp3"
            
            # --- RETRY LOGIC (3x) ---
            success = False
            for attempt in range(3):
                # PANGGIL LEWAT SUBPROCESS
                if await run_edge_tts_command(chunk, selected_voice, temp_file):
                    # Cek file size > 0
                    if os.path.exists(temp_file) and os.path.getsize(temp_file) > 0:
                        success = True
                        break
                
                # Jika gagal, tunggu sebentar
                await asyncio.sleep(2)
            
            if not success: return None
            temp_files.append(temp_file)

        # Merge
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
                    if extract: text += extract + " "
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
        return f"{INTERNAL_ERROR_FLAG}Gagal Baca File: {str(e)}"
    
    return clean_text_formatting(text)