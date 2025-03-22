
document.addEventListener("DOMContentLoaded", () => {
  fetch('/api/weather')
  .then(response => response.json())
  .then(data => {
    console.log(data);
    // Build your Chart.js chart here
    const ctx = document.getElementById("barChart");

    new Chart(ctx, {
      type: "bar",
      data: {
        labels: [Object.values(data["location"])],
        datasets: [
          {
            label: "AirTemp",
            data: data["airTemp"],
            borderWidth: 1,
          },
        ],
      },
      options: {
        scales: {
          y: {
            beginAtZero: true,
          },
        },
      },
    });
  });  
});
