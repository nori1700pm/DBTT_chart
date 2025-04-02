import datetime
import streamlit as st
import markdown
import requests
import pandas as pd
import random


# Function to fetch weather data
@st.cache_data(ttl=300)
def fetch_weather_data():
    try:
        response = requests.get("http://127.0.0.1:5000/api/weather/current")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error fetching data: {e}")
        return []


# Function to calculate average statistics
def calculate_average_stats(data):
    if not data:
        return {}

    avg = lambda values: sum(values) / len(values) if values else None

    return {
        "Temperature (°C)": avg([d["airTemp"] for d in data]),
        "Heat Stress": avg([d["heatStress"] for d in data]),
        "Humidity (%)": avg([d["humidity"] for d in data]),
        "Wind Speed (m/s)": avg([d["windSpeed"] for d in data]),
        "Wind Direction": data[0]["windDirection_dir"] if data else None,
    }


def generate_time_series(current):
    now = datetime.datetime.now()
    time_labels = []
    stress_values = []

    for i in range(-3, 4):  # Simulating past and future values
        time = now + datetime.timedelta(hours=i)
        time_labels.append(time.strftime("%H:%M"))

        temp = current["Temperature (°C)"] + (random.uniform(-0.6, 0.6))
        wind = current["Wind Speed (m/s)"] + (random.uniform(-0.2, 0.2))
        humidity = current["Humidity (%)"] + (random.uniform(-0.75, 0.75))

        wbgt = 0.726330 * temp + 0.012713 * wind + 0.109697 * humidity - 5.12977
        stress_values.append(wbgt)

    return pd.DataFrame({"Time": time_labels, "Heat Stress": stress_values})


# Custom CSS for styling
def apply_custom_css():
    st.markdown(
        """
        <style>
            .stApp {
                background-color: #f4f4f9;
                font-family: 'Arial', sans-serif;
            }
            .stButton>button {
                background-color: #4CAF50;
                color: white;
                border-radius: 8px;
                padding: 10px 20px;
                font-size: 16px;
            }
            .stTextInput>div>input, .stSelectbox>div>select {
                padding: 10px;
                border-radius: 5px;
                border: 1px solid #ccc;
            }
            .recommendation-box {
                background-color: #e8f7ea;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            st-key-recommendation-box {
                background-color: #e8f7ea;
                padding: 20px;
                border-radius: 10px;
                margin-top: 20px;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            h1, h2, h3 {
                color: #333;
            }
        </style>
    """,
        unsafe_allow_html=True,
    )


# Function to simulate API call for weather data
def fetch_weather_recommendation(postal_code, house_direction):
    res = requests.get(
        "http://127.0.0.1:5000/api/ai/suggestions",
        params={"postal_code": postal_code, "direction": house_direction},
    )
    if res.status_code != 200:
        st.error("Failed to fetch weather data. Please try again later.")
        return None, None
    data = res.json()
    # Simulate API response (replace with actual API call)
    weather_station_data = data["data"]["weather_station_data"]
    average_weather_stats = {}
    for station in weather_station_data:
        keys = ["airTemp", "humidity", "windSpeed", "uv_index"]
        for key in keys:
            average_weather_stats[key] = (
                average_weather_stats.get(key, 0)
                + station[key] * station["distance_weight"]
            )

    average_weather_stats["uv_index"] = int(average_weather_stats["uv_index"])
    # Remove everything before "Summary:"
    if "Summary:" in data["suggestion"]:
        suggestions = data["suggestion"].split("Summary:")[1].strip()
        suggestions = "\n**Summary:** " + suggestions
        suggestions = suggestions.replace("Suggestions:", "\n**Suggestions:** ")
    return average_weather_stats, markdown.markdown(suggestions)


# Main function
def main():
    # Apply custom CSS
    apply_custom_css()

    # Title and description
    st.title("🏡 Home Weather Advisor")
    st.subheader("Get personalized tips to stay cool and save energy!")
    # Fetch Data
    weather_data = fetch_weather_data()

    if weather_data:
        avg_stats = calculate_average_stats(weather_data)

        # Display Average Statistics
        st.subheader("Average Statistics")
        col1, col2, col3 = st.columns(3)

        col1.metric("Temperature (°C)", f"{avg_stats['Temperature (°C)']:.1f}°C")
        col2.metric("Heat Stress", f"{avg_stats['Heat Stress']:.0f}")
        col3.metric("Wind Direction", avg_stats["Wind Direction"])

        # Display Overall Statistics Table
        st.subheader("Overall Statistics")
        metric_options = [
            "Temperature (°C)",
            "Humidity (%)",
            "Wind Speed (m/s)",
            "Heat Stress",
        ]
        metric_mapper = {
            "Temperature (°C)": "airTemp",
            "Humidity (%)": "humidity",
            "Wind Speed (m/s)": "windSpeed",
            "Heat Stress": "heatStress",
        }
        selected_metric = st.selectbox("Select Metric:", metric_options)
        print(weather_data)

        room_data = [
            {
                "Room": d["room"],
                selected_metric: f"{d[metric_mapper[selected_metric]] : .1f}",
            }
            for d in weather_data
        ]
        st.table(pd.DataFrame(room_data))

        # Predictive Heat Stress Graph
        st.subheader("Predictive Heat Stress Time Series")
        stress_df = generate_time_series(avg_stats)
        st.pyplot(
            stress_df.set_index("Time")
            .plot(
                title="Predictive Heat Stress Time Series",
                xlabel="Time",
                ylabel="Heat Stress (WBGT)",
                figsize=(10, 5),
            )
            .get_figure()
        )

    else:
        st.warning("No weather data available.")
        st.write(
            "Enter your postal code and house direction to receive tailored recommendations based on current weather conditions."
        )

    # User inputs
    postal_code = st.text_input(
        "Postal Code", max_chars=6, placeholder="Enter your postal code"
    )
    house_direction = st.number_input(
        "House Direction (in degrees)",
        min_value=0,
        max_value=360,
        value=0,
        step=1,
        help="Enter the direction your house faces in degrees (0-360).",
    )
    disabled = (
        len(postal_code.strip()) != 6
        or not postal_code.strip().isdigit()
        or not house_direction
    )

    # Submit button
    if st.button("Generate Recommendations", disabled=disabled):
        if postal_code.strip() == "":
            st.error("Please enter a valid postal code.")
        else:
            # Fetch weather data and recommendations
            with st.spinner("Fetching weather data and generating recommendations..."):
                weather_data, recommendations = fetch_weather_recommendation(
                    postal_code, house_direction
                )

            # Display weather summary
            st.subheader("Weather Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Temperature", f"{weather_data['airTemp']:.1f} °C")
            col2.metric("Humidity", f"{weather_data['humidity']:.1f} %")
            col3.metric("UV Index", weather_data["uv_index"])
            col4.metric("Wind Speed", f"{weather_data['windSpeed']:.1f} km/h")

            # Display recommendations inside the styled box
            st.subheader("Personalized Recommendations")
            if recommendations:
                st.markdown(
                    f'<div class="recommendation-box">{recommendations}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.info(
                    "No specific recommendations available for the current weather conditions."
                )


# Run the app
if __name__ == "__main__":
    main()
