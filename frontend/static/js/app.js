/* ══════════════════════════════════════════════════════════════════
   app.js – main application logic
   Handles: GPS, search, data fetching, rendering, offline, theme
══════════════════════════════════════════════════════════════════ */
'use strict';

// ── App state ──────────────────────────────────────────────────────
const State = {
    lat: null,
    lon: null,
    units: localStorage.getItem('wx_units') || 'metric',
    theme: localStorage.getItem('wx_theme') || 'auto',
    cityName: localStorage.getItem('wx_cityName') || '',
    data: null,
};

// ── Bootstrap ──────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
    applyStoredTheme();
    document.getElementById('unitSelect').value = State.units;
    registerServiceWorker();
    monitorNetwork();
    detectGPS();
    bindSearchInput();
});

// ── GPS & location ──────────────────────────────────────────────────
function detectGPS() {
    if (!navigator.geolocation) { loadDefault(); return; }
    showLoading(true);
    navigator.geolocation.getCurrentPosition(
        pos => {
            State.lat = pos.coords.latitude;
            State.lon = pos.coords.longitude;
            reverseGeocode(State.lat, State.lon).then(name => {
                State.cityName = name;
                loadAll();
            });
        },
        err => {
            console.warn('GPS denied:', err.message);
            loadDefault();
        }, { timeout: 8000, maximumAge: 60000 }
    );
}

function loadDefault() {
    // Fallback: Mumbai
    State.lat = 19.0760;
    State.lon = 72.8777;
    State.cityName = 'Mumbai, IN';
    loadAll();
}

async function reverseGeocode(lat, lon) {
    try {
        const r = await fetch(`/api/weather/reverse-geocode/?lat=${lat}&lon=${lon}`);
        const d = await r.json();
        return d.name ? `${d.name}, ${d.country}` : `${lat.toFixed(2)}, ${lon.toFixed(2)}`;
    } catch { return `${lat.toFixed(2)}, ${lon.toFixed(2)}`; }
}

// ── Main data loader ────────────────────────────────────────────────
async function loadAll() {
    showLoading(true);
    try {
        const url = `/api/weather/full/?lat=${State.lat}&lon=${State.lon}&units=${State.units}`;
        const r = await fetch(url);
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const d = await r.json();
        State.data = d;
        persistCache(d);
        renderAll(d);
        connectWebSocket();
        loadSavedLocations();
    } catch (err) {
        console.error('loadAll error:', err);
        loadFromCache();
    } finally {
        showLoading(false);
    }
}

function reloadData() {
    State.units = document.getElementById('unitSelect').value;
    localStorage.setItem('wx_units', State.units);
    if (State.lat) loadAll();
}

// ── Render ─────────────────────────────────────────────────────────
function renderAll(d) {
    renderCurrent(d.current);
    renderAlerts(d.alerts);
    renderMetrics(d.current);
    renderAQI(d.aqi);
    renderLifestyle(d.lifestyle);
    renderDaily(d.daily);
    updateDayNight(d.current.sunrise, d.current.sunset, d.current.timezone_offset);
    drawHourlyChart(d.hourly); // charts.js
    updateMap(State.lat, State.lon); // map.js
    updateWebSocketLocation();
}

function renderCurrent(c) {
    const u = State.units;
    const deg = u === 'imperial' ? '°F' : u === 'standard' ? 'K' : '°C';
    const spd = u === 'imperial' ? 'mph' : 'm/s';

    $('cityName', State.cityName || '–');
    $('localTime', fmtLocalTime(Date.now(), c.timezone_offset));
    $('tempValue', `${Math.round(c.temp)}${deg}`);
    $('tempMax', `${Math.round(c.temp_max)}${deg}`);
    $('tempMin', `${Math.round(c.temp_min)}${deg}`);
    $('feelsLike', `Feels like ${Math.round(c.feels_like)}${deg}`);
    $('description', c.description);
    $('sunrise', fmtTime(c.sunrise, c.timezone_offset));
    $('sunset', fmtTime(c.sunset, c.timezone_offset));

    const icon = document.getElementById('weatherIcon');
    icon.src = `https://openweathermap.org/img/wn/${c.icon}@2x.png`;
    icon.alt = c.description;
}

function renderMetrics(c) {
    const u = State.units;
    const spd = u === 'imperial' ? 'mph' : 'm/s';
    $('humidity', `${c.humidity}%`);
    $('dewPoint', c.dew_point != null ? `${Math.round(c.dew_point)}°` : '–');
    $('wind', `${c.wind_speed} ${spd} ${bearingToCompass(c.wind_deg)}`);
    $('gusts', `${c.wind_gust} ${spd}`);
    $('visibility', `${(c.visibility / 1000).toFixed(1)} km`);
    $('pressure', `${c.pressure} hPa`);
    $('uvIndex', uviLabel(c.uv_index));
    $('rain', `${c.rain_1h} mm`);
    $('snow', `${c.snow_1h} mm`);
    $('cloudCover', `${c.cloud_cover}%`);
}

function renderAlerts(alerts) {
    const el = document.getElementById('alertBanner');
    if (!el) return;
    if (alerts && alerts.length) {
        const a = alerts[0];
        el.innerHTML = `⚠️ <strong>${a.event}</strong>: ${a.description.slice(0, 160)}…`;
        el.className = `alert-banner ${a.severity || ''}`;
    } else {
        el.className = 'alert-banner hidden';
    }
}

function renderAQI(aqi) {
    const AQI_COLORS = { 1: '#22c55e', 2: '#84cc16', 3: '#facc15', 4: '#f97316', 5: '#ef4444' };
    const circle = document.getElementById('aqiCircle');
    circle.textContent = aqi.aqi;
    circle.style.backgroundColor = AQI_COLORS[aqi.aqi] || '#94a3b8';
    $('aqiLabel', aqi.label || '–');
    $('aqiGuidance', aqi.guidance || '–');
    $('pm25', `${(aqi.pm2_5 || 0).toFixed(1)} μg/m³`);
    $('pm10', `${(aqi.pm10  || 0).toFixed(1)} μg/m³`);
    $('o3', `${(aqi.o3    || 0).toFixed(1)} μg/m³`);
    $('no2', `${(aqi.no2   || 0).toFixed(1)} μg/m³`);
    $('so2', `${(aqi.so2   || 0).toFixed(1)} μg/m³`);
    $('co', `${(aqi.co    || 0).toFixed(1)} μg/m³`);
}

function renderLifestyle(l) {
    $('lifestyleContent', `
    <p>👗 <strong>Clothing:</strong> ${l.clothing.join(', ')}</p>
    <p>🏃 <strong>Outdoor:</strong> ${l.outdoor.join(' • ')}</p>
    <p>🕶 <strong>Sun safety:</strong> ${l.sun_protection}</p>
  `);
}

function renderDaily(days) {
    const u = State.units;
    const deg = u === 'imperial' ? '°F' : '°C';
    const strip = document.getElementById('forecastStrip');
    strip.innerHTML = days.slice(0, 7).map(d => `
    <div class="day-card" role="listitem">
      <div class="day-name">${fmtDay(d.dt)}</div>
      <img src="https://openweathermap.org/img/wn/${d.icon}.png"
           alt="${d.description}" width="40" height="40" loading="lazy" />
      <div>${Math.round(d.temp_max)}${deg} / ${Math.round(d.temp_min)}${deg}</div>
      <div>${d.description}</div>
      <div class="rain-prob">🌧 ${Math.round(d.rain_prob * 100)}%</div>
    </div>
  `).join('');
}

// ── Day / Night background ─────────────────────────────────────────
function updateDayNight(sunriseTs, sunsetTs, tzOffset) {
    const utcNow = Date.now() / 1000;
    const localNow = utcNow + (tzOffset || 0);
    const isDay = localNow >= sunriseTs && localNow <= sunsetTs;
    const bg = document.getElementById('dayNightBg');
    bg.className = `day-night-bg ${isDay ? 'day' : 'night'}`;
    if (State.theme === 'auto') {
        document.body.classList.toggle('dark-mode', !isDay);
    }
}

// ── Theme ──────────────────────────────────────────────────────────
function toggleTheme() {
    const isDark = document.body.classList.toggle('dark-mode');
    State.theme = isDark ? 'dark' : 'light';
    localStorage.setItem('wx_theme', State.theme);
    document.getElementById('themeToggle').textContent = isDark ? '☀️' : '🌙';
}

function applyStoredTheme() {
    if (State.theme === 'dark') {
        document.body.classList.add('dark-mode');
        document.getElementById('themeToggle').textContent = '☀️';
    }
}

// ── Search ─────────────────────────────────────────────────────────
function bindSearchInput() {
    const input = document.getElementById('citySearch');
    let debounce;
    input.addEventListener('input', () => {
        clearTimeout(debounce);
        debounce = setTimeout(() => autoComplete(input.value.trim()), 300);
    });
    input.addEventListener('keydown', e => { if (e.key === 'Enter') searchLocation(); });
}

async function autoComplete(q) {
    const dd = document.getElementById('searchDropdown');
    if (q.length < 2) { dd.classList.add('hidden'); return; }
    const r = await fetch(`/api/weather/search/?q=${encodeURIComponent(q)}`);
    const data = await r.json();
    if (!data.length) { dd.classList.add('hidden'); return; }
    dd.innerHTML = data.map(d => `
    <li onclick="pickSearchResult(${d.lat}, ${d.lon}, '${d.name}, ${d.country}')">
      ${d.name}, ${d.state ? d.state + ', ' : ''}${d.country}
    </li>
  `).join('');
    dd.classList.remove('hidden');
}

function pickSearchResult(lat, lon, name) {
    State.lat = lat;
    State.lon = lon;
    State.cityName = name;
    document.getElementById('citySearch').value = name;
    document.getElementById('searchDropdown').classList.add('hidden');
    loadAll();
}

async function searchLocation() {
    const q = document.getElementById('citySearch').value.trim();
    if (!q) return;
    const r = await fetch(`/api/weather/search/?q=${encodeURIComponent(q)}`);
    const data = await r.json();
    if (data.length) pickSearchResult(data[0].lat, data[0].lon, `${data[0].name}, ${data[0].country}`);
}


// ── Offline / cache ────────────────────────────────────────────────
function persistCache(d) { try { localStorage.setItem('wx_cache', JSON.stringify(d)); } catch {} }

function loadFromCache() {
    try {
        const raw = localStorage.getItem('wx_cache');
        if (raw) { renderAll(JSON.parse(raw));
            showOfflineToast(); }
    } catch {}
}

function monitorNetwork() {
    window.addEventListener('offline', showOfflineToast);
    window.addEventListener('online', () => {
        document.getElementById('offlineToast').classList.add('hidden');
        loadAll();
    });
}

function showOfflineToast() {
    document.getElementById('offlineToast').classList.remove('hidden');
}

function registerServiceWorker() {
    if ('serviceWorker' in navigator)
        navigator.serviceWorker.register('/static/js/sw.js').catch(console.warn);
}

// ── Utils ──────────────────────────────────────────────────────────
function $(id, html) { const el = document.getElementById(id); if (el) el.innerHTML = html; }

function fmtTime(ts, tzOff = 0) {
    if (!ts) return '–';
    const d = new Date((ts + tzOff) * 1000);
    return d.toISOString().slice(11, 16); // HH:MM UTC-adjusted
}

function fmtLocalTime(ms, tzOff = 0) {
    const d = new Date(ms + (tzOff * 1000));
    return d.toUTCString().replace(' GMT', '');
}

function fmtDay(ts) {
    return new Date(ts * 1000).toLocaleDateString([], { weekday: 'short' });
}

const DIRS = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE', 'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW'];

function bearingToCompass(deg) { return DIRS[Math.round((deg % 360) / 22.5) % 16]; }

function uviLabel(uvi) {
    if (uvi <= 2) return `${uvi} Low`;
    if (uvi <= 5) return `${uvi} Moderate`;
    if (uvi <= 7) return `${uvi} High`;
    if (uvi <= 10) return `${uvi} Very High`;
    return `${uvi} Extreme`;
}

function getToken() { return localStorage.getItem('wx_token'); }

function authHeader() {
    const t = getToken();
    return t ? { Authorization: `Bearer ${t}` } : {};
}

function showLoading(v) {
    document.getElementById('loadingOverlay').classList.toggle('hidden', !v);
}

// Expose for WebSocket callbacks
function updateWebSocketLocation() {
    if (window._wsLocationId) window.connectWeatherWS && window.connectWeatherWS(window._wsLocationId);
}