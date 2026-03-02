// Chart.js version: 4.5.1
// To upgrade: replace static/js/vendor/chart.umd.min.js with the new UMD build.

const COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2',
  '#59a14f', '#edc948', '#b07aa1', '#ff9da7',
  '#9c755f', '#bab0ac',
];

function buildDoughnut(canvasId, dataScriptId, total) {
  const raw = JSON.parse(document.getElementById(dataScriptId).textContent);
  if (!raw.length) return;

  new Chart(document.getElementById(canvasId), {
    type: 'doughnut',
    data: {
      labels: raw.map(d => d.name),
      datasets: [{
        data: raw.map(d => d.total),
        backgroundColor: COLORS.slice(0, raw.length),
        borderWidth: 1,
      }],
    },
    options: {
      plugins: {
        tooltip: {
          callbacks: {
            label: ctx => {
              const val = ctx.parsed;
              const pct = total > 0 ? ((val / total) * 100).toFixed(1) : '0.0';
              return ` ${ctx.label}: ${val.toFixed(2)} (${pct}%)`;
            },
          },
        },
      },
    },
  });
}

document.addEventListener('DOMContentLoaded', function () {
  const expenseTotal = parseFloat(document.getElementById('expense-total-value').dataset.value);
  const earningTotal = parseFloat(document.getElementById('earning-total-value').dataset.value);
  buildDoughnut('expense-chart', 'expense-chart-data', expenseTotal);
  buildDoughnut('earning-chart', 'earning-chart-data', earningTotal);
});
