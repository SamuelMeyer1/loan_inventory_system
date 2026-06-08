let statusChart = null;
let loansChart = null;
let jobStatusChart = null;
let dueBucketsChart = null;
let topBorrowersChart = null;

const chartPalette = ["#2f6f8f", "#4f9f6f", "#d89a2b", "#b04a3a", "#6b7c93", "#8a63a8"];
const chartBaseOptions = {
  responsive: true,
  maintainAspectRatio: false,
  devicePixelRatio: Math.max(2, window.devicePixelRatio || 1),
};

function chartRows(state, key) {
  return state.statistics?.[key] || [];
}

function resetChart(chart) {
  if (chart) chart.destroy();
}

function renderStatusChart(state) {
  const ctx = document.getElementById("statusChart");
  if (!ctx) return;
  const rows = chartRows(state, "object_status");
  resetChart(statusChart);
  statusChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: rows.map((row) => row.label || "Okand"),
      datasets: [{ data: rows.map((row) => row.value), backgroundColor: chartPalette }],
    },
    options: { ...chartBaseOptions, plugins: { legend: { position: "bottom" } } },
  });
}

function renderJobStatusChart(state) {
  const ctx = document.getElementById("jobStatusChart");
  if (!ctx) return;
  const labels = { requested: "Request", prepared: "Redo att hamta", loaned: "Lanad", returned: "Aterlamnad", stocked: "Lagerford" };
  const rows = chartRows(state, "job_status");
  resetChart(jobStatusChart);
  jobStatusChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map((row) => labels[row.label] || row.label),
      datasets: [{ label: "Jobb", data: rows.map((row) => row.value), backgroundColor: "#2f6f8f" }],
    },
    options: { ...chartBaseOptions, plugins: { legend: { display: false } } },
  });
}

function renderLoansPerMonthChart(state) {
  const ctx = document.getElementById("loansPerMonthChart");
  if (!ctx) return;
  const rows = chartRows(state, "loans_per_month");
  resetChart(loansChart);
  loansChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: rows.map((row) => row.label),
      datasets: [
        { label: "Lan", data: rows.map((row) => row.loans), borderColor: "#2f6f8f", backgroundColor: "rgba(47, 111, 143, 0.14)", tension: 0.3 },
        { label: "Antal artiklar", data: rows.map((row) => row.quantity), borderColor: "#4f9f6f", backgroundColor: "rgba(79, 159, 111, 0.12)", tension: 0.3 },
      ],
    },
    options: chartBaseOptions,
  });
}

function renderDueBucketsChart(state) {
  const ctx = document.getElementById("dueBucketsChart");
  if (!ctx) return;
  const rows = chartRows(state, "due_buckets");
  resetChart(dueBucketsChart);
  dueBucketsChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: rows.map((row) => row.label),
      datasets: [{ data: rows.map((row) => row.value), backgroundColor: ["#b04a3a", "#d89a2b", "#2f6f8f", "#6b7c93"] }],
    },
    options: { ...chartBaseOptions, plugins: { legend: { position: "bottom" } } },
  });
}

function renderTopBorrowersChart(state) {
  const ctx = document.getElementById("topBorrowersChart");
  if (!ctx) return;
  const rows = chartRows(state, "top_borrowers");
  resetChart(topBorrowersChart);
  topBorrowersChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: rows.map((row) => row.label),
      datasets: [{ label: "Utlånade artiklar", data: rows.map((row) => row.value), backgroundColor: "#4f9f6f" }],
    },
    options: { ...chartBaseOptions, indexAxis: "y", plugins: { legend: { display: false } } },
  });
}

function renderAllStatisticsCharts(state) {
  renderStatusChart(state);
  renderJobStatusChart(state);
  renderLoansPerMonthChart(state);
  renderDueBucketsChart(state);
  renderTopBorrowersChart(state);
}
