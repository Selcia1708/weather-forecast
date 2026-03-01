/* ══════════════════════════════════════════════════════════════════
   map.js – Leaflet radar map with OWM tile layers
══════════════════════════════════════════════════════════════════ */
'use strict';
(function () {
  let map          = null;
  let weatherLayer = null;
  let marker       = null;
  const OWM_KEY    = document.body.dataset.owmKey || '';

  const LAYERS = {
    precipitation_new: 'Precipitation',
    clouds_new:        'Clouds',
    wind_new:          'Wind Speed',
    temp_new:          'Temperature',
  };

  function initMap() {
    if (map) return;
    map = L.map('radarMap', { zoomControl: true, attributionControl: true })
           .setView([20, 78], 4);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://openstreetmap.org">OpenStreetMap</a>',
      maxZoom: 18,
    }).addTo(map);

    setMapLayer('precipitation_new', document.querySelector('.map-btn'));
  }

  window.updateMap = function (lat, lon) {
    if (!map) initMap();
    map.setView([lat, lon], 8);

    if (marker) map.removeLayer(marker);
    marker = L.marker([lat, lon])
               .addTo(map)
               .bindPopup('📍 Your location')
               .openPopup();
  };

  window.setMapLayer = function (layerId, btn) {
    if (!map) initMap();
    if (weatherLayer) map.removeLayer(weatherLayer);

    if (OWM_KEY) {
      weatherLayer = L.tileLayer(
        `https://tile.openweathermap.org/map/${layerId}/{z}/{x}/{y}.png?appid=${OWM_KEY}`,
        { opacity: 0.65, maxZoom: 18, attribution: '© OpenWeatherMap' }
      ).addTo(map);
    }

    // Toggle active button
    document.querySelectorAll('.map-btn').forEach(b => b.classList.remove('active'));
    if (btn) btn.classList.add('active');
  };

  document.addEventListener('DOMContentLoaded', initMap);
})();