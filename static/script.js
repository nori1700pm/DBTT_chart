document.addEventListener("DOMContentLoaded", () => {
  Promise.all([
    fetch('/api/weather').then(response => response.json()),
    fetch('/api/uv_index').then(response => response.json()),
    fetch('/api/2hr_forecast').then(response => response.json())
  ])
  .then(([data, uvData, forecastData]) => {
    console.log("Weather Data:", data);
    console.log("UV Index Data:", uvData);
    console.log("2-Hour Forecast Data:", forecastData);

    console.log(data);
    console.log(Object.values(data["location"]));

    // edit widget values
    const forecast = document.getElementById("forecast");
    forecast.innerText = Object.values(forecastData.forecast)[0];
    
    // Your existing Chart.js code remains untouched
    const ctx = document.getElementById("barChart");
    const lineChart = document.getElementById('lineChart')

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

    new Chart(ctx, {
      type: "line",
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
