from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import requests
import json
import base64
import io
import os
import time
from datetime import datetime, timedelta
from dotenv import load_dotenv
from PIL import Image

load_dotenv()

app = Flask(__name__)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-lite")
GEMINI_FALLBACK_MODELS = ("gemini-2.5-flash-lite", "gemini-flash-lite-latest")


def api_keys_configured():
    return bool(GEMINI_API_KEY and OPENWEATHER_API_KEY)


def prepare_image(img_bytes, max_size=1024):
    """Kecilkan gambar agar hemat kuota token Gemini."""
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    img.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return buf.getvalue()


def is_gemini_quota_error(err):
    text = str(err).lower()
    return "429" in str(err) or "quota" in text or "resourceexhausted" in text


def gemini_error_message(err):
    if is_gemini_quota_error(err):
        return (
            "Kuota Gemini free tier habis (batas per menit atau per hari). "
            "Tunggu ~1 menit lalu coba lagi, atau buat API key baru di Google AI Studio."
        )
    if "API_KEY_INVALID" in str(err) or "api key" in str(err).lower():
        return "Gemini API key tidak valid"
    return f"Terjadi kesalahan: {err}"


def analyze_image_with_gemini(gemini_key, prompt, img_bytes):
    genai.configure(api_key=gemini_key)
    models = [GEMINI_MODEL, *[m for m in GEMINI_FALLBACK_MODELS if m != GEMINI_MODEL]]
    last_err = None

    for model_name in models:
        for attempt in range(2):
            try:
                model = genai.GenerativeModel(model_name)
                return model.generate_content([
                    prompt,
                    {"mime_type": "image/jpeg", "data": img_bytes},
                ])
            except Exception as e:
                last_err = e
                if is_gemini_quota_error(e) and attempt == 0:
                    time.sleep(21)
                    continue
                if is_gemini_quota_error(e):
                    break
                raise

    raise last_err

def calculate_risk_score(disease_data, weather_data):
    score = 0
    factors = []

    # 1. Base score dari severity penyakit
    severity_map = {"rendah": 20, "sedang": 45, "tinggi": 70, "tidak berlaku": 0}
    severity = disease_data.get("severity", "tidak berlaku")
    base = severity_map.get(severity, 0)
    if not disease_data.get("is_healthy", True):
        score += base
        factors.append({"label": "Kondisi Daun Saat Ini", "value": base, "max": 70})

    # 2. Faktor kelembapan (kondisi optimal jamur/bakteri: >80%)
    humidity = weather_data.get("humidity", 50)
    hum_score = 0
    if humidity >= 85:
        hum_score = 20
        factors.append({"label": "Kelembapan Sangat Tinggi", "value": 20, "max": 20})
    elif humidity >= 70:
        hum_score = 12
        factors.append({"label": "Kelembapan Tinggi", "value": 12, "max": 20})
    elif humidity >= 55:
        hum_score = 5
        factors.append({"label": "Kelembapan Sedang", "value": 5, "max": 20})
    score += hum_score

    # 3. Faktor suhu (optimal penyakit jamur: 20-30°C)
    temp = weather_data.get("temp", 25)
    temp_score = 0
    if 22 <= temp <= 30:
        temp_score = 10
        factors.append({"label": "Suhu Optimal Patogen", "value": 10, "max": 10})
    elif 18 <= temp <= 35:
        temp_score = 5
        factors.append({"label": "Suhu Mendukung Patogen", "value": 5, "max": 10})
    score += temp_score

    # 4. Faktor hujan / curah hujan
    rain = weather_data.get("rain_1h", 0)
    rain_score = 0
    if rain > 5:
        rain_score = 15
        factors.append({"label": "Curah Hujan Lebat", "value": 15, "max": 15})
    elif rain > 1:
        rain_score = 8
        factors.append({"label": "Hujan Ringan-Sedang", "value": 8, "max": 15})
    score += rain_score

    # 5. Cap di 100
    score = min(score, 100)

    # 6. Risk level label
    if score >= 70:
        level = "TINGGI"
        color = "#E05A4A"
        bg = "#2A1410"
    elif score >= 40:
        level = "SEDANG"
        color = "#F0C040"
        bg = "#2A2410"
    else:
        level = "RENDAH"
        color = "#4CAF72"
        bg = "#112A18"

    return {
        "score": score,
        "level": level,
        "color": color,
        "bg": bg,
        "factors": factors
    }


def generate_action_plan(disease_data, weather_data, risk_data):
    today = datetime.now()
    plan = []

    risk_score = risk_data["score"]
    is_healthy = disease_data.get("is_healthy", True)

    if is_healthy and risk_score < 40:
        plan = [
            {"day": (today + timedelta(days=0)).strftime("%A, %d %b"), "hari": "Hari ini", "action": "Lakukan inspeksi visual rutin pada seluruh tanaman", "priority": "rendah"},
            {"day": (today + timedelta(days=2)).strftime("%A, %d %b"), "hari": "2 hari lagi", "action": "Pastikan drainase lahan baik jika hujan diprediksi", "priority": "rendah"},
            {"day": (today + timedelta(days=5)).strftime("%A, %d %b"), "hari": "5 hari lagi", "action": "Pemberian pupuk sesuai jadwal rutin", "priority": "rendah"},
            {"day": (today + timedelta(days=7)).strftime("%A, %d %b"), "hari": "7 hari lagi", "action": "Upload foto baru untuk monitoring berkala", "priority": "rendah"},
        ]
    elif risk_score < 70:
        plan = [
            {"day": (today + timedelta(days=0)).strftime("%A, %d %b"), "hari": "Hari ini", "action": "Isolasi tanaman yang terinfeksi dari tanaman sehat", "priority": "sedang"},
            {"day": (today + timedelta(days=1)).strftime("%A, %d %b"), "hari": "Besok", "action": "Aplikasikan fungisida/bakterisida sesuai jenis penyakit", "priority": "tinggi"},
            {"day": (today + timedelta(days=2)).strftime("%A, %d %b"), "hari": "2 hari lagi", "action": "Kurangi kelembapan sekitar tanaman, perbaiki sirkulasi udara", "priority": "sedang"},
            {"day": (today + timedelta(days=4)).strftime("%A, %d %b"), "hari": "4 hari lagi", "action": "Evaluasi efektivitas penanganan, cek perkembangan gejala", "priority": "sedang"},
            {"day": (today + timedelta(days=7)).strftime("%A, %d %b"), "hari": "7 hari lagi", "action": "Upload foto ulang untuk verifikasi pemulihan", "priority": "rendah"},
        ]
    else:
        plan = [
            {"day": (today + timedelta(days=0)).strftime("%A, %d %b"), "hari": "Hari ini — SEGERA", "action": "Karantina ketat: isolasi dan tandai semua tanaman bergejala", "priority": "tinggi"},
            {"day": (today + timedelta(days=0)).strftime("%A, %d %b"), "hari": "Hari ini", "action": "Buang dan musnahkan bagian daun/batang yang terinfeksi parah", "priority": "tinggi"},
            {"day": (today + timedelta(days=1)).strftime("%A, %d %b"), "hari": "Besok pagi", "action": "Aplikasikan fungisida sistemik dosis penuh, ulangi 3 hari sekali", "priority": "tinggi"},
            {"day": (today + timedelta(days=2)).strftime("%A, %d %b"), "hari": "2 hari lagi", "action": "Konsultasikan ke penyuluh pertanian atau ahli tanaman setempat", "priority": "tinggi"},
            {"day": (today + timedelta(days=4)).strftime("%A, %d %b"), "hari": "4 hari lagi", "action": "Evaluasi menyeluruh: jika menyebar, pertimbangkan eradikasi parsial", "priority": "tinggi"},
            {"day": (today + timedelta(days=7)).strftime("%A, %d %b"), "hari": "7 hari lagi", "action": "Upload foto ulang untuk monitoring wajib", "priority": "sedang"},
        ]

    return plan


@app.route("/")
def index():
    return render_template("index.html", api_keys_configured=api_keys_configured())


@app.route("/analyze", methods=["POST"])
def analyze():
    try:
        data = request.get_json()
        gemini_key = data.get("gemini_key", "").strip() or GEMINI_API_KEY
        weather_key = data.get("weather_key", "").strip() or OPENWEATHER_API_KEY
        image_b64 = data.get("image", "")
        city = data.get("city", "Jakarta").strip()
        lat = data.get("lat")
        lon = data.get("lon")

        if not gemini_key:
            return jsonify({"error": "Gemini API key diperlukan"}), 400
        if not weather_key:
            return jsonify({"error": "OpenWeatherMap API key diperlukan"}), 400
        if not image_b64:
            return jsonify({"error": "Gambar diperlukan"}), 400

        if lat and lon:
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?lat={lat}&lon={lon}&appid={weather_key}&units=metric"
        else:
            weather_url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={weather_key}&units=metric"

        weather_resp = requests.get(weather_url, timeout=10)
        if weather_resp.status_code == 401:
            try:
                detail = weather_resp.json().get("message", "API key tidak valid")
            except Exception:
                detail = "API key tidak valid"
            return jsonify({
                "error": (
                    f"OpenWeatherMap: {detail}. "
                    "Konfirmasi email akun di inbox, lalu tunggu hingga 2 jam agar key aktif."
                )
            }), 400
        if weather_resp.status_code == 404:
            return jsonify({"error": f"Kota '{city}' tidak ditemukan. Coba nama kota dalam Bahasa Inggris."}), 400
        if weather_resp.status_code != 200:
            return jsonify({"error": "Gagal mengambil data cuaca"}), 500

        weather_raw = weather_resp.json()
        weather_data = {
            "city": weather_raw.get("name", city),
            "country": weather_raw.get("sys", {}).get("country", ""),
            "temp": weather_raw.get("main", {}).get("temp", 25),
            "feels_like": weather_raw.get("main", {}).get("feels_like", 25),
            "humidity": weather_raw.get("main", {}).get("humidity", 60),
            "description": weather_raw.get("weather", [{}])[0].get("description", "-").title(),
            "wind_speed": weather_raw.get("wind", {}).get("speed", 0),
            "rain_1h": weather_raw.get("rain", {}).get("1h", 0),
            "clouds": weather_raw.get("clouds", {}).get("all", 0),
            "icon": weather_raw.get("weather", [{}])[0].get("icon", "01d"),
        }

        img_bytes = prepare_image(base64.b64decode(image_b64.split(",")[-1]))

        PROMPT = f"""
Kamu adalah ahli patologi tanaman berpengalaman. Analisis gambar daun ini secara mendalam.

Kondisi cuaca saat ini di lokasi petani:
- Suhu: {weather_data['temp']}°C
- Kelembapan: {weather_data['humidity']}%
- Kondisi: {weather_data['description']}
- Curah hujan 1 jam terakhir: {weather_data['rain_1h']} mm

Balas HANYA dalam format JSON berikut (tanpa markdown, tanpa teks di luar JSON):

{{
  "is_plant_leaf": true/false,
  "plant_type": "jenis tanaman",
  "is_healthy": true/false,
  "disease_name": "nama penyakit dalam Bahasa Indonesia",
  "disease_name_latin": "nama ilmiah",
  "pathogen_type": "jamur/bakteri/virus/nutrisi/lainnya",
  "severity": "rendah/sedang/tinggi/tidak berlaku",
  "confidence": angka 0-100,
  "symptoms_visible": "gejala yang terlihat di gambar (2-3 kalimat)",
  "weather_impact": "bagaimana kondisi cuaca saat ini mempengaruhi risiko penyebaran (2 kalimat)",
  "spread_risk_7days": "prediksi risiko penyebaran 7 hari ke depan berdasarkan cuaca (2 kalimat)",
  "immediate_action": "tindakan paling mendesak yang harus dilakukan sekarang (1 kalimat)",
  "estimated_crop_loss": "estimasi persentase kerugian panen jika tidak ditangani (contoh: 20-40%)"
}}
"""
        response = analyze_image_with_gemini(gemini_key, PROMPT, img_bytes)

        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        disease_data = json.loads(raw)

        risk_data = calculate_risk_score(disease_data, weather_data)
        action_plan = generate_action_plan(disease_data, weather_data, risk_data)

        return jsonify({
            "disease": disease_data,
            "weather": weather_data,
            "risk": risk_data,
            "action_plan": action_plan,
            "analyzed_at": datetime.now().strftime("%d %B %Y, %H:%M WIB")
        })

    except json.JSONDecodeError:
        return jsonify({"error": "Gagal memproses respons AI. Coba dengan foto yang lebih jelas."}), 500
    except Exception as e:
        status = 429 if is_gemini_quota_error(e) else 500
        return jsonify({"error": gemini_error_message(e)}), status


if __name__ == "__main__":
    app.run(debug=True, port=5000)
