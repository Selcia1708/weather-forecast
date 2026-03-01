/* ══════════════════════════════════════════════════════════════════
   realtime.js – WebSocket client for live weather push
══════════════════════════════════════════════════════════════════ */
'use strict';
(function () {
  let ws            = null;
  let locationId    = null;
  let retryCount    = 0;
  const MAX_RETRIES = 10;
  const BASE_DELAY  = 3000;  // ms

  window.connectWeatherWS = function (locId) {
    if (!locId) return;
    locationId = locId;
    window._wsLocationId = locId;
    retryCount = 0;
    _connect();
  };

  function _connect() {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close();
    }
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/ws/weather/${locationId}/`);

    ws.onopen = () => {
      console.info('[WS] Connected to location', locationId);
      retryCount = 0;
    };

    ws.onmessage = e => {
      const msg = JSON.parse(e.data);

      if (msg.type === 'weather_update' && msg.data) {
        // Merge into existing state and re-render affected panels
        if (msg.data.current)   renderCurrent(msg.data.current);
        if (msg.data.aqi)       renderAQI(msg.data.aqi);
        if (msg.data.alerts)    renderAlerts(msg.data.alerts);
        if (msg.data.lifestyle) renderLifestyle(msg.data.lifestyle);
        console.debug('[WS] weather_update received');
      }

      if (msg.type === 'severe_alert') {
        showAlertToast(msg.alert);
      }
    };

    ws.onclose = code => {
      console.warn('[WS] Closed with code', code);
      if (retryCount < MAX_RETRIES) {
        const delay = BASE_DELAY * Math.pow(1.5, retryCount);
        retryCount++;
        console.info(`[WS] Reconnecting in ${(delay/1000).toFixed(1)}s (attempt ${retryCount})`);
        setTimeout(_connect, delay);
      } else {
        console.error('[WS] Max retries reached – falling back to polling');
        startPollingFallback();
      }
    };

    ws.onerror = err => console.error('[WS] Error', err);
  }

  function showAlertToast(alert) {
    const t = document.createElement('div');
    t.className = 'toast alert-toast';
    t.innerHTML = `⚠️ <strong>${alert.event}</strong>`;
    document.body.appendChild(t);
    setTimeout(() => t.remove(), 6000);
  }

  function startPollingFallback() {
    setInterval(() => {
      if (typeof loadAll === 'function') loadAll();
    }, 5 * 60 * 1000);  // every 5 min
  }
})();