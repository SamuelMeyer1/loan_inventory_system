// charts.js

let statusChart = null;
let loansChart = null;


function renderLoansPerMonthChart(state) {
  const ctx = document.getElementById("loansPerMonthChart");
  if (!ctx) return;

  const counts = {};

  state.loans.forEach(loan => {
    if (!loan.checkout_time) return;

    const date = new Date(loan.checkout_time.replace(" ", "T"));
    const key = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

    counts[key] = (counts[key] || 0) + 1;
  });

  const labels = Object.keys(counts).sort();
  const data = labels.map(l => counts[l]);

  if (loansChart) {
    loansChart.destroy();
  }

  loansChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: labels,
      datasets: [{
        label: "Lån per månad",
        data: data,
        tension: 0.3
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}



function renderStatusChart(state) {

    
  const ctx = document.getElementById("statusChart");
  if (!ctx) return;

  // Räkna status
    const available = state.objects.filter(o => o.status === "Tillgänglig").length;
    const unvailable = state.objects.filter(o => o.status === "Utlånad").length;
    const empty = state.objects.filter(o => o.status === "Slut").length;
    const low = state.objects.filter(o => o.status === "Låg nivå").length;

  // Om redan finns → destroy (viktigt!)
  if (statusChart) {
    statusChart.destroy();
  }

  statusChart = new Chart(ctx, {
    type: "doughnut",
    data: {
        labels: ["Tillgänglig", "Utlånad", "Slut", "Låg nivå"],
        datasets: [{
        data: [available, unvailable, empty, low],
        }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom"
        }
      }
    }
  });
}