# 🌾 CropRisk — Sistem Peringatan Dini Penyakit Tanaman

> Mini project inovatif: deteksi penyakit daun + cuaca real-time → risk score + jadwal tindakan 7 hari

---

## 🚀 Cara Jalankan

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Dapatkan API Keys (keduanya GRATIS)

**Gemini API Key:**
→ https://aistudio.google.com/app/apikey

**OpenWeatherMap API Key:**
→ https://openweathermap.org/api (daftar → API Keys)
⚠️ Tunggu ~10 menit setelah daftar agar key aktif

### 3. Jalankan server
```bash
python app.py
```

### 4. Buka browser
```
http://localhost:5000
```

---

## 📁 Struktur Project
```
croprisk/
├── app.py                  # Flask backend + risk engine
├── requirements.txt
├── README.md
├── templates/
│   └── index.html          # Main UI
└── static/
    ├── css/style.css       # Styling
    └── js/main.js          # Frontend logic
```

---

## ✨ Fitur Inovatif

### 🔬 Multi-Source Analysis
- **Foto daun** → Gemini AI analisis penyakit, gejala, patogen
- **Cuaca real-time** → OpenWeatherMap (suhu, kelembapan, hujan)
- **Risk Scoring Engine** → gabungkan keduanya jadi skor 0-100

### 📊 Risk Score Components
| Faktor | Max Poin |
|--------|----------|
| Tingkat keparahan penyakit | 70 |
| Kelembapan udara | 20 |
| Suhu lingkungan | 10 |
| Curah hujan | 15 |

### 📅 Output Utama
- **Indeks Risiko 0-100** dengan visualisasi donut chart
- **Prediksi penyebaran 7 hari** berbasis kondisi cuaca
- **Estimasi kerugian panen** jika tidak ditangani
- **Jadwal tindakan harian** yang dipersonalisasi berdasarkan level risiko
- **Deteksi lokasi GPS** otomatis

---

## 🛠️ Tech Stack
- **Backend**: Flask (Python)
- **AI**: Google Gemini 1.5 Flash
- **Cuaca**: OpenWeatherMap API
- **Frontend**: HTML/CSS/JS (tanpa framework)
- **Font**: Syne + JetBrains Mono + Inter

---

## 💡 Poin Inovasi untuk Presentasi
1. **Bukan sekedar klasifikasi** — ini decision support system
2. **Data fusion**: gabungkan computer vision + environmental data
3. **Predictive**, bukan reactive — peringatan sebelum penyakit parah
4. **Action-oriented output** — petani tahu harus ngapain hari ini

---

## 📝 Catatan
- Free tier Gemini: 15 req/menit, 1500 req/hari
- Free tier OpenWeatherMap: 60 req/menit, 1.000.000 req/bulan
- Foto terbaik: fokus pada daun, pencahayaan cukup, resolusi jelas
