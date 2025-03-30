document.addEventListener("DOMContentLoaded", () => {
  Promise.all([
    fetch('/api/weather/current').then(response => response.json()), // returns indoor data
  ])
  .then(([data]) => {
    feather.replace();
    console.log("Weather Data:", data);

    // add date time
    const now = new Date();
    const formatted = now.toLocaleString("en-SG", {
      dateStyle: "medium",
      timeStyle: "short"
    });
    document.getElementById("current-datetime").textContent = formatted;

    // Metrics for overall stats table
    let metricIndex = 0;
    const metricKeys = ["airTemp", "humidity", "windSpeed", "heatStress"];
    const metricLabels = {
      airTemp: "Temperature (°C)",
      humidity: "Humidity (%)",
      windSpeed: "Wind Speed (m/s)",
      heatStress: "Heat Stress"
    };


    // function get stats
    function renderAverageStats(data){
      if (!data.length) return;

      // calculate mean of an array of number
      const avg = arr => arr.reduce((a, b) => a + b, 0) / arr.length;
    
      const airTempAvg = avg(data.map(d => d.airTemp)).toFixed(1);
      const heatStressAvg = avg(data.map(d => d.heatStress)).toFixed(0);
      const humidityAvg = avg(data.map(d => d.humidity));
      const windSpeedAvg = avg(data.map(d => d.windSpeed));
      const windDirection = data[0].windDirection_dir; 
    
      // Determine labels
      const tempLabel = airTempAvg < 27 ? "Normal" : "Warm";
      const heatLabel = heatStressAvg < 28 ? "Normal" : heatStressAvg < 32 ? "Moderate" : "High";
    
      // Update DOM
      document.getElementById("avg-temp").innerHTML = `
        <strong>Temperature:</strong> <span style="color:#c28700">${airTempAvg}°C</span>
      `;
    
      document.getElementById("avg-heat").innerHTML = `
        <strong>Heat Stress:</strong> <span style="color:#f57c00">${heatStressAvg}</span>
      `;
    
      document.getElementById("avg-wind").innerHTML = `
        <strong>Wind Direction:</strong> <span>${windDirection}</span>
      `;

      const current = {
        airTemp: parseFloat(airTempAvg),
        humidity: humidityAvg,
        windSpeed: windSpeedAvg
      };

      renderHeatStressChart(current);
    }

    function renderOverallStats(data){
      const currentMetric = metricKeys[metricIndex];
      const table = document.getElementById("room-metric-table");
      const label = document.getElementById("metric-label");
    
      let html = "<tr><th style='text-align:left;'>Room</th><th style='text-align:center;'>" + metricLabels[currentMetric] + "</th></tr>";
    
      for (const row of data) {
        const value = row[currentMetric]?.toFixed(1) || "-";
        html += `<tr>
          <td>${row.room}</td>
          <td style="text-align:center;">${value}</td>
        </tr>`;
      }

      table.innerHTML = html;
      label.textContent = metricLabels[currentMetric];
    }

    renderAverageStats(data)
    renderOverallStats(data)

    // Attach arrow button events
    document.getElementById("prevMetric").addEventListener("click", () => {
      metricIndex = (metricIndex - 1 + metricKeys.length) % metricKeys.length;
      renderOverallStats(data);
    });

    document.getElementById("nextMetric").addEventListener("click", () => {
      metricIndex = (metricIndex + 1) % metricKeys.length;
      renderOverallStats(data);
    });

  
    // Chart Code
    function generateTimeSeries(current) {
      const now = new Date();
      const timeLabels = [];
      const stressValues = [];
    
      for (let i = -3; i <= 3; i++) {
        const time = new Date(now);
        time.setHours(time.getHours() + i);
        timeLabels.push(time.toLocaleTimeString("en-SG", { hour: '2-digit', minute: '2-digit' }));
    
        // Simulate slight variation
        const temp = current.airTemp + (Math.random() * 1.2 - 0.6);      // ±0.6°C
        const wind = current.windSpeed + (Math.random() * 0.4 - 0.2);    // ±0.2 m/s
        const humidity = current.humidity + (Math.random() * 1.5 - 0.75); // ±0.75%
    
        const wbgt = (
          0.726330 * temp +
          0.012713 * wind +
          0.109697 * humidity -
          5.12977
        );
    
        stressValues.push(Number(wbgt.toFixed(2)));
      }
    
      return { timeLabels, stressValues };
    }
    

    function renderHeatStressChart(current) {
      const { timeLabels, stressValues } = generateTimeSeries(current);
    
      const ctx = document.getElementById("heatStressChart");
      new Chart(ctx, {
        type: "line",
        data: {
          labels: timeLabels,
          datasets: [{
            label: "Heat Stress (WBGT)",
            data: stressValues,
            fill: false,
            tension: 0.3,
            borderWidth: 2,
            pointRadius: 3
          }]
        },
        options: {
          scales: {
            y: {
              beginAtZero: false,
              title: { 
                display: true, 
                text: "WBGT Index",
                font: {
                  size: 10
                }}
            },
            x: {
              title: { 
                display: true, 
                text: "Time", 
                font:{
                size:10
                }},
              ticks: {
                maxTicksLimit: 4, // limits the number of labels shown
                maxRotation: 0,
                minRotation: 0
              }
            }
          }
        }
      });
    }
    


  });  
});
