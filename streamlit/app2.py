import streamlit as st
import requests

# Custom CSS for styling
def apply_custom_css():
    st.markdown("""
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
            h1, h2, h3 {
                color: #333;
            }
        </style>
    """, unsafe_allow_html=True)

# Function to simulate API call for weather data
def fetch_weather_recommendation(postal_code, house_direction):
    
    # Simulate API response (replace with actual API call)
    weather_data = {
        "temperature": 32,  # in Celsius
        "humidity": 70,     # in percentage
        "uv_index": 8,
        "wind_speed": 15,   # in km/h
    }

    # Generate recommendations based on weather data
    recommendations = []
    if weather_data["temperature"] > 30:
        recommendations.append("Use fans or air conditioning to stay cool.")
    if weather_data["humidity"] > 60:
        recommendations.append("Consider using a dehumidifier to reduce indoor humidity.")
    if weather_data["uv_index"] > 7:
        recommendations.append(f"Close curtains on the {house_direction}-facing windows to reduce heat from sunlight.")
    if weather_data["wind_speed"] > 10:
        recommendations.append("Open windows on opposite sides of the house to create cross-ventilation.")

    return weather_data, recommendations

# Main function
def main():
    # Apply custom CSS
    apply_custom_css()

    # Title and description
    st.title("🏡 Home Weather Advisor")
    st.subheader("Get personalized tips to stay cool and save energy!")
    st.write("Enter your postal code and house direction to receive tailored recommendations based on current weather conditions.")

    # User inputs
    postal_code = st.text_input("PostalCodes", placeholder="Enter your postal code")
    house_direction = st.selectbox("House Direction", ["North", "South", "East", "West"])

    # Submit button
    if st.button("Generate Recommendations"):
        if postal_code.strip() == "":
            st.error("Please enter a valid postal code.")
        else:
            # Fetch weather data and recommendations
            with st.spinner("Fetching weather data and generating recommendations..."):
                weather_data, recommendations = fetch_weather_recommendation(postal_code, house_direction)

            # Display weather summary
            st.subheader("Weather Summary")
            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Temperature", f"{weather_data['temperature']} °C")
            col2.metric("Humidity", f"{weather_data['humidity']} %")
            col3.metric("UV Index", weather_data["uv_index"])
            col4.metric("Wind Speed", f"{weather_data['wind_speed']} km/h")

            # Display recommendations inside the styled box
            st.subheader("Personalized Recommendations")
            if recommendations:
                # Use HTML to create the recommendation box
                st.markdown('<div class="recommendation-box">', unsafe_allow_html=True)
                for rec in recommendations:
                    st.markdown(f"<p style='margin: 5px 0;'>- {rec}</p>", unsafe_allow_html=True)
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.info("No specific recommendations available for the current weather conditions.")

# Run the app
if __name__ == "__main__":
    main()