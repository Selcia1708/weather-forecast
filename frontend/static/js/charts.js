/* ══════════════════════════════════════════════════════════════════
   charts.js – Chart.js hourly forecast chart
══════════════════════════════════════════════════════════════════ */
'use strict';
(function () {
  let hourlyChart = null;

  window.drawHourlyChart = function (hours) {
    const ctx    = document.getElementById('hourlyChart');
    if (!ctx) return;
    const labels  = hours.map(h => fmtHour(h.dt));
    const temps   = hours.map(h => parseFloat(h.temp.toFixed(1)));
    const rain    = hours.map(h => Math.round((h.rain_prob || 0) * 100));
    const isDark  = document.body.classList.contains('dark-mode');
    const gridClr = isDark ? 'rgba(255,255,255,.08)' : 'rgba(0,0,0,.08)';
    const textClr = isDark ? '#94a3b8' : '#64748b';

    if (hourlyChart) hourlyChart.destroy();

    hourlyChart = new Chart(ctx, {
      data: {
        labels,
        datasets: [
          {
            type: 'line',
            label: 'Temperature',
            data: temps,
            borderColor:     '#f97316',
            backgroundColor: 'rgba(249,115,22,.1)',
            fill: true,
            tension: 0.4,
            pointRadius: 3,
            yAxisID: 'yTemp',
          },
          {
            type: 'bar',
            label: 'Rain %',
            data: rain,
            backgroundColor: 'rgba(59,130,246,.45)',
            borderRadius: 4,
            yAxisID: 'yRain',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        interaction: { mode: 'index', intersect: false },
        plugins: {
          legend: { labels: { color: textClr, boxWidth: 12 } },
          tooltip: {
            callbacks: {
              label: ctx => ctx.dataset.label === 'Rain %'
                ? `Rain: ${ctx.raw}%`
                : `Temp: ${ctx.raw}°`,
            },
          },
        },
        scales: {
          x: {
            ticks: { color: textClr, maxTicksLimit: 12 },
            grid:  { color: gridClr },
          },
          yTemp: {
            position: 'left',
            ticks:    { color: '#f97316' },
            grid:     { color: gridClr },
            title:    { display: true, text: 'Temp', color: '#f97316' },
          },
          yRain: {
            position: 'right',
            min: 0, max: 100,
            ticks:    { color: '#3b82f6', callback: v => `${v}%` },
            grid:     { drawOnChartArea: false },
            title:    { display: true, text: 'Rain %', color: '#3b82f6' },
          },
        },
      },
    });
  };

  function fmtHour(ts) {
    return new Date(ts * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }
})();