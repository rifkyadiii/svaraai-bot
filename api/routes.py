import os
import shutil
import uuid
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
import services

# Membuat Router
router = APIRouter()

# --- HELPER: Hapus File Setelah Download ---
def cleanup_file(path: str):
    if os.path.exists(path):
        os.remove(path)

# --- 1. ENDPOINT OCR (Gambar -> Teks) ---
@router.post("/api/ocr")
async def api_ocr(file: UploadFile = File(...)):
    try:
        # Baca bytes gambar langsung dari RAM
        content = await file.read()
        text = services.ocr_with_gemini(content)

        if not text:
            raise HTTPException(status_code=400, detail="Gagal membaca gambar.")

        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 2. ENDPOINT EXTRACT FILE (PDF/DOCX -> Teks) ---
@router.post("/api/extract")
async def api_extract(file: UploadFile = File(...)):
    temp_path = f"temp_api_{uuid.uuid4()}_{file.filename}"
    try:
        # Simpan file upload ke disk sementara
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Ekstrak
        text = services.extract_document_content(temp_path)

        if not text:
            raise HTTPException(status_code=400, detail="File kosong atau tidak terbaca.")

        return {"status": "success", "text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Bersihkan file temp
        cleanup_file(temp_path)

# --- 3. ENDPOINT SUMMARIZE (Teks -> Ringkasan) ---
@router.post("/api/summarize")
async def api_summarize(text: str = Form(...)):
    try:
        summary = services.summarize_text(text)
        if summary.startswith("⚠️"):
             raise HTTPException(status_code=500, detail=summary)
        return {"status": "success", "summary": summary}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 4. ENDPOINT TRANSLATE (Teks -> Terjemahan) ---
@router.post("/api/translate")
async def api_translate(text: str = Form(...), target_lang: str = Form(...)):
    try:
        result = services.translate_text(text, target_lang)
        return {"status": "success", "translated_text": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- 5. ENDPOINT TTS (Teks -> Audio File) ---
@router.post("/api/tts")
async def api_tts(
    background_tasks: BackgroundTasks,
    text: str = Form(...),
    lang: str = Form(...),
    gender: str = Form(...)
):
    try:
        # Generate Audio
        # Gunakan 'api_user' sebagai ID dummy
        filename = await services.generate_audio(text, lang, gender, f"api_{uuid.uuid4()}")

        if not filename:
            raise HTTPException(status_code=500, detail="Gagal generate audio.")

        # Jadwalkan penghapusan file setelah file terkirim ke user
        background_tasks.add_task(cleanup_file, filename)

        return FileResponse(filename, media_type="audio/mpeg", filename="tts_output.mp3")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))