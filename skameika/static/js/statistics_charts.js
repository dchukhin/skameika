// Chart.js version: 4.5.1
// To upgrade: replace static/js/vendor/chart.umd.min.js with the new UMD build.

document.addEventListener('DOMContentLoaded', function () {
  const raw = JSON.parse(document.getElementById('statistics-chart-data').textContent);
  if (!raw.length) return;

  new Chart(document.getElementById('statistics-chart'), {
    type: 'line',
    data: {
      labels: raw.map(d => d.month),
      datasets: [{
        label: document.getElementById('statistics-chart').dataset.label,
        data: raw.map(d => d.amount),
        borderColor: '#4e79a7',
        backgroundColor: 'rgba(78,121,167,0.1)',
        tension: 0.2,
        fill: true,
      }],
    },
    options: {
      scales: { y: { beginAtZero: false } },
    },
  });
});
