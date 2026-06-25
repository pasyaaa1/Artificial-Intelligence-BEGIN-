let imageBase64 = null;
let gpsCoords = null;

const DONUT_CIRCUMFERENCE = 314;
const SEVERITY_CLASS = { rendah: 'green', sedang: 'yellow', tinggi: 'red' };

// ─── Init ─────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  updateClock();
  setInterval(updateClock, 1000);

  document.getElementById('fileInput').addEventListener('change', handleFile);
  document.getElementById('uploadZone').addEventListener('click', () => {
    document.getElementById('fileInput').click();
  });
  document.getElementById('gpsBtn').addEventListener('click', getGPS);
  document.getElementById('analyzeBtn').addEventListener('click', analyze);
  document.getElementById('resetBtn').addEventListener('click', resetForm);

  setupDragDrop();
});

function updateClock() {
  const now = new Date();
  const time = now.toLocaleTimeString('id-ID', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  });
  document.getElementById('clock').textContent = `${time} WIB`;
}

function escapeHtml(str) {
  if (str == null) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// ─── Upload ───────────────────────────────────────
function handleFile(event) {
  const file = event.target.files[0];
  if (file) loadImage(file);
}

function loadImage(file) {
  const reader = new FileReader();
  reader.onload = (e) => {
    imageBase64 = e.target.result;
    document.getElementById('previewImg').src = imageBase64;
    document.getElementById('previewImg').classList.remove('hidden');
    document.getElementById('uploadPlaceholder').classList.add('hidden');
  };
  reader.readAsDataURL(file);
}

function setupDragDrop() {
  const zone = document.getElementById('uploadZone');
  zone.addEventListener('dragover', (e) => {
    e.preventDefault();
    zone.classList.add('dragover');
  });
  zone.addEventListener('dragleave', () => zone.classList.remove('dragover'));
  zone.addEventListener('drop', (e) => {
    e.preventDefault();
    zone.classList.remove('dragover');
    const file = e.dataTransfer.files[0];
    if (file?.type.startsWith('image/')) loadImage(file);
  });
}

// ─── GPS ──────────────────────────────────────────
function getGPS() {
  const status = document.getElementById('gpsStatus');
  const btn = document.getElementById('gpsBtn');

  if (!navigator.geolocation) {
    status.textContent = 'Browser tidak mendukung deteksi lokasi.';
    status.style.color = 'var(--red)';
    return;
  }

  btn.disabled = true;
  status.textContent = 'Mendeteksi lokasi...';
  status.style.color = 'var(--accent)';

  navigator.geolocation.getCurrentPosition(
    (pos) => {
      gpsCoords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
      status.textContent = `Lokasi: ${gpsCoords.lat.toFixed(4)}, ${gpsCoords.lon.toFixed(4)}`;
      status.style.color = 'var(--accent)';
      btn.disabled = false;
    },
    () => {
      status.textContent = 'Gagal mendeteksi lokasi. Isi nama kota manual.';
      status.style.color = 'var(--red)';
      btn.disabled = false;
      gpsCoords = null;
    }
  );
}

// ─── Analyze ──────────────────────────────────────
async function analyze() {
  const apiConfigured = window.CROPRISK_API_CONFIGURED === true;
  const geminiEl = document.getElementById('geminiKey');
  const weatherEl = document.getElementById('weatherKey');
  const geminiKey = geminiEl ? geminiEl.value.trim() : '';
  const weatherKey = weatherEl ? weatherEl.value.trim() : '';
  const city = document.getElementById('cityInput').value.trim();

  if (!apiConfigured && !geminiKey) return showError('Masukkan Gemini API key terlebih dahulu.');
  if (!apiConfigured && !weatherKey) return showError('Masukkan OpenWeatherMap API key terlebih dahulu.');
  if (!imageBase64) return showError('Upload foto daun terlebih dahulu.');
  if (!city && !gpsCoords) return showError('Isi nama kota atau gunakan deteksi lokasi.');

  hideError();
  setLoading(true);

  try {
    const payload = { gemini_key: geminiKey, weather_key: weatherKey, image: imageBase64, city };
    if (gpsCoords) {
      payload.lat = gpsCoords.lat;
      payload.lon = gpsCoords.lon;
    }

    const res = await fetch('/analyze', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });

    const data = await res.json();
    if (!res.ok) {
      showError(data.error || 'Terjadi kesalahan pada server.');
      return;
    }

    renderResult(data);
  } catch {
    showError('Gagal terhubung ke server. Pastikan aplikasi berjalan.');
  } finally {
    setLoading(false);
  }
}

// ─── Render ───────────────────────────────────────
function renderResult(data) {
  const { disease, weather, risk, action_plan, analyzed_at } = data;

  document.getElementById('resultSection').classList.remove('hidden');
  document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth', block: 'start' });

  renderRisk(risk, analyzed_at);
  renderWeather(weather);
  renderDisease(disease);
  renderPrediction(disease, risk);
  renderActionPlan(action_plan);
}

function renderRisk(risk, analyzedAt) {
  const hero = document.getElementById('riskHero');
  hero.style.background = risk.bg;
  hero.style.borderColor = risk.color + '33';

  const fill = document.getElementById('donutFill');
  const numEl = document.getElementById('riskNumber');
  fill.style.stroke = risk.color;
  fill.style.strokeDashoffset = DONUT_CIRCUMFERENCE - (DONUT_CIRCUMFERENCE * risk.score / 100);
  numEl.style.color = risk.color;

  animateNumber(numEl, risk.score);

  const badge = document.getElementById('riskLevelBadge');
  badge.textContent = `Risiko ${risk.level.toLowerCase()}`;
  badge.style.color = risk.color;

  document.getElementById('riskAnalyzed').textContent = `Dianalisis: ${analyzedAt}`;

  const factorsEl = document.getElementById('riskFactors');
  if (!risk.factors.length) {
    factorsEl.innerHTML = '<p class="empty-note">Tidak ada faktor risiko signifikan.</p>';
    return;
  }

  factorsEl.innerHTML = risk.factors.map((f) => `
    <div class="factor-item">
      <div class="factor-label">
        <span>${escapeHtml(f.label)}</span>
        <span class="factor-pts">+${f.value}</span>
      </div>
      <div class="factor-bar-wrap">
        <div class="factor-bar" style="width:${(f.value / f.max) * 100}%"></div>
      </div>
    </div>
  `).join('');
}

function renderWeather(weather) {
  document.getElementById('weatherIcon').src =
    `https://openweathermap.org/img/wn/${weather.icon}@2x.png`;
  document.getElementById('weatherTemp').textContent = `${Math.round(weather.temp)}°C`;
  document.getElementById('weatherDesc').textContent = weather.description;
  document.getElementById('weatherLoc').textContent = `${weather.city}, ${weather.country}`;

  const stats = [
    ['Kelembapan', `${weather.humidity}%`],
    ['Angin', `${weather.wind_speed} m/s`],
    ['Hujan 1j', `${weather.rain_1h} mm`],
    ['Awan', `${weather.clouds}%`],
  ];

  document.getElementById('weatherStats').innerHTML = stats.map(([label, val]) => `
    <div class="w-stat">
      <div class="w-stat-label">${label}</div>
      <div class="w-stat-val">${val}</div>
    </div>
  `).join('');
}

function renderDisease(disease) {
  const el = document.getElementById('diseaseResult');

  if (!disease.is_plant_leaf) {
    el.innerHTML = '<p class="d-val">Gambar tidak terdeteksi sebagai daun tanaman. Coba foto yang lebih jelas.</p>';
    return;
  }

  const title = disease.is_healthy
    ? `${disease.plant_type} — sehat`
    : disease.disease_name;
  const sevClass = SEVERITY_CLASS[disease.severity] || '';

  el.innerHTML = `
    <div class="disease-name">${escapeHtml(title)}</div>
    ${disease.disease_name_latin ? `<div class="disease-latin">${escapeHtml(disease.disease_name_latin)}</div>` : ''}
    <div class="disease-tags">
      <span class="dtag">${escapeHtml(disease.plant_type)}</span>
      ${disease.pathogen_type ? `<span class="dtag">${escapeHtml(disease.pathogen_type)}</span>` : ''}
      ${disease.is_healthy
        ? '<span class="dtag green">Sehat</span>'
        : `<span class="dtag ${sevClass}">Keparahan: ${escapeHtml(disease.severity)}</span>`}
    </div>
    <div class="conf-row">
      <span class="conf-label">Keyakinan</span>
      <div class="conf-bar-wrap">
        <div class="conf-bar" style="width:${disease.confidence}%"></div>
      </div>
      <span class="conf-pct">${disease.confidence}%</span>
    </div>
    <div class="d-section">
      <div class="d-label">Gejala terdeteksi</div>
      <div class="d-val">${escapeHtml(disease.symptoms_visible)}</div>
    </div>
    ${disease.immediate_action ? `
    <div class="d-section">
      <div class="d-label">Tindakan segera</div>
      <div class="d-val highlight">${escapeHtml(disease.immediate_action)}</div>
    </div>` : ''}
  `;
}

function renderPrediction(disease, risk) {
  document.getElementById('predictionGrid').innerHTML = `
    <div class="pred-item">
      <div class="pred-item-label">Dampak cuaca saat ini</div>
      <div class="pred-item-val">${escapeHtml(disease.weather_impact || '—')}</div>
    </div>
    <div class="pred-item">
      <div class="pred-item-label">Prediksi penyebaran 7 hari</div>
      <div class="pred-item-val">${escapeHtml(disease.spread_risk_7days || '—')}</div>
    </div>
    <div class="pred-item">
      <div class="pred-item-label">Estimasi kerugian panen</div>
      <div class="stat-highlight">${escapeHtml(disease.estimated_crop_loss || 'N/A')}</div>
      <div class="stat-note">jika tidak ditangani</div>
    </div>
    <div class="pred-item">
      <div class="pred-item-label">Skor risiko gabungan</div>
      <div class="stat-highlight" style="color:${risk.color}">${risk.score}/100</div>
      <div class="stat-note">berdasarkan kondisi daun dan cuaca</div>
    </div>
  `;
}

function renderActionPlan(actionPlan) {
  document.getElementById('actionTimeline').innerHTML = actionPlan.map((item) => `
    <div class="timeline-item">
      <div class="tl-left">
        <div class="tl-marker priority-${item.priority}"></div>
        <div class="tl-day">${escapeHtml(item.day)}</div>
      </div>
      <div class="tl-right">
        <div class="tl-hari priority-${item.priority}">${escapeHtml(item.hari)}</div>
        <div class="tl-action">${escapeHtml(item.action)}</div>
      </div>
    </div>
  `).join('');
}

function animateNumber(el, target) {
  let count = 0;
  const step = Math.max(1, Math.ceil(target / 30));
  const timer = setInterval(() => {
    count = Math.min(count + step, target);
    el.textContent = count;
    if (count >= target) clearInterval(timer);
  }, 25);
}

// ─── UI helpers ───────────────────────────────────
function setLoading(loading) {
  const btn = document.getElementById('analyzeBtn');
  document.getElementById('btnText').classList.toggle('hidden', loading);
  document.getElementById('btnLoader').classList.toggle('hidden', !loading);
  btn.disabled = loading;
}

function showError(msg) {
  const box = document.getElementById('errorBox');
  box.textContent = msg;
  box.classList.remove('hidden');
  box.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
  document.getElementById('errorBox').classList.add('hidden');
}

function resetForm() {
  document.getElementById('resultSection').classList.add('hidden');
  imageBase64 = null;
  gpsCoords = null;
  document.getElementById('previewImg').classList.add('hidden');
  document.getElementById('uploadPlaceholder').classList.remove('hidden');
  document.getElementById('fileInput').value = '';
  document.getElementById('gpsStatus').textContent = '';
  document.getElementById('cityInput').value = '';
  hideError();
  window.scrollTo({ top: 0, behavior: 'smooth' });
}
