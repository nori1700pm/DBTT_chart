
document.addEventListener("DOMContentLoaded", () => {
  fetch('/api/weather')
  .then(response => response.json())
  .then(data => {
    console.log(data);
    console.log(Object.values(data["location"]))
    // Build your Chart.js chart here
    const ctx = document.getElementById("barChart");

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: Object.values(data["location"]),
        datasets: [
          {
            label: "AirTemp",
            data: Object.values(data["airTemp"]),
            borderWidth: 1,
          },
        ],
      },
      options: {
        scales: {
          x: {
            ticks: {
              autoSkip: false,
              maxRotation: 90,
              minRotation: 90
            }
          },
        
          y: {
            beginAtZero: true,
          },
        },
      },
    });
  });  
});
