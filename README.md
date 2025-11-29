# 🤖 SvaraAI Bot: Intelligent NLP Assistant

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Hybrid-green)
![Gemini AI](https://img.shields.io/badge/AI-Google%20Gemini%202.0-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

**Sistem Bot Multiguna: OCR, Ringkasan, Terjemahan, dan Teks-ke-Suara**

## 🔍 Tentang SvaraAI

SvaraAI merupakan bot serbaguna berbasis **Artificial Intelligence** yang dirancang untuk membantu mahasiswa dan profesional memproses dokumen dengan cepat. Proyek ini menggunakan arsitektur **Hybrid**, berfungsi sebagai Bot Telegram interaktif sekaligus REST API.

---

## 🚀 Akses Online

### 🤖 Coba Bot di Telegram:
Silakan cari username berikut di Telegram untuk mencoba langsung:
**[@svaraai_bot](https://t.me/@svaraai_bot)**
*(Ganti dengan username bot asli Anda, misal @SvaraUAS_Bot)*

### 🌐 Dokumentasi API (Swagger UI):
Untuk pengujian integrasi Frontend/Web, akses dokumentasi API di sini:
**[https://NAMA-PROJECT-RENDER.onrender.com](https://NAMA-PROJECT-RENDER.onrender.com)**
*(Ganti dengan URL Render Anda)*

---

## ✨ Fitur Utama & Teknologi

SvaraAI dibangun menggunakan teknologi sebagai berikut:

### 1. 📄 Optical Character Recognition (OCR)
Mengekstrak teks dari foto buku, catatan tangan, atau dokumen cetak.
* **Teknologi:** `Google Gemini 2.0 Flash (Vision)`
  
### 2. 📝 Ringkasan Teks Otomatis (Abstractive)
Meringkas dokumen panjang menjadi paragraf narasi yang mengalir (bukan sekadar poin-poin kaku).
* **Teknologi:** `Google Gemini 2.0 Flash (LLM)`

### 3. 🌍 Terjemahan Kontekstual
Menerjemahkan dokumen dengan memahami konteks kalimat, bukan kata-per-kata.
* **Teknologi:** `Google Gemini 2.0 Flash`

### 4. 🔊 Neural Text-to-Speech (TTS)
Mengubah teks menjadi suara manusia yang sangat natural (ada intonasi dan helaan napas).
* **Teknologi:** `Edge-TTS` (Microsoft Azure Neural Speech).
* **Fitur:** Tersedia pilihan suara **Pria & Wanita** untuk setiap bahasa.
* **Bahasa Support:** 🇮🇩 Indonesia, 🇺🇸 Inggris, 🇯🇵 Jepang, 🇰🇷 Korea, 🇸🇦 Arab.

### 5. 📦 Smart File Handling
* **Statistik:** Menampilkan jumlah kata & huruf secara realtime.
* **Anti-Spam:** Otomatis mengirim file `.txt` jika teks terlalu panjang (>300 kata) agar chat tidak penuh.

---

## ⚙️ Konfigurasi & Instalasi

Ikuti langkah ini untuk menjalankan di komputer lokal (Localhost):

### 1. Clone Repository
```bash
git clone [https://github.com/rifkyadiii/svaraai-bot.git](https://github.com/rifkyadiii/svaraai-bot.git)
cd svaraai-bot
````

### 2\. Setup Environment Variables

Buat file bernama `.env` di folder root, lalu isi dengan kredensial Anda:

```env
TELEGRAM_TOKEN=masukkan_token_dari_botfather_disini
GEMINI_API_KEY=masukkan_api_key_google_ai_studio_disini
```

### 3\. Install Dependencies

Pastikan Python sudah terinstall, lalu jalankan:

```bash
pip install -r requirements.txt
```

-----

## ▶️ Cara Menjalankan

### Menjalankan Server (Bot + API)

```bash
python main.py
```

  * Bot Telegram akan otomatis aktif.
  * API Server berjalan di `http://localhost:8000`.

-----

## 📂 Struktur Proyek

```text
svaraai_bot/
│── main.py           # Entry Point (Server FastAPI & Loader Bot)
│── handlers.py       # Logika Interaksi Bot Telegram (Menu, Button, Reply)
│── services.py       # "Otak" AI (Logic Gemini, OCR, TTS, Translate)
└── api/routes.py     # Endpoint REST API (Untuk akses Frontend/Flutter)
│── config.py         # Konfigurasi Global & Environment Variables
│── .env              # File Rahasia (Token & Key)
└── requirements.txt  # Daftar Pustaka Python
```

-----

## 🛠️ Tech Stack

  * **Language:** Python 3.10+
  * **Framework:** FastAPI, Uvicorn
  * **Bot Library:** Python-Telegram-Bot (Async)
  * **AI Engine:** Google Generative AI SDK
  * **TTS Engine:** Edge-TTS
  * **Deployment:** Render / Docker

-----
