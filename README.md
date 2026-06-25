# CropRisk

Web app untuk analisis penyakit daun tanaman. Upload foto, tentukan lokasi, lalu dapat skor risiko berdasarkan kondisi daun dan cuaca sekitar.

## Setup

```bash
pip install -r requirements.txt
```

Buat file `.env` dari template:

```bash
copy .env.example .env
```

Isi API key di `.env`:

- Gemini: https://aistudio.google.com/app/apikey
- OpenWeatherMap: https://openweathermap.org/api (key aktif setelah ~10 menit)

Jalankan:

```bash
python app.py
```

Buka http://localhost:5000

## Struktur

```
app.py
requirements.txt
.env.example
templates/index.html
static/css/style.css
static/js/main.js
```
