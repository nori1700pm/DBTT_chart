from flask import Flask, render_template, jsonify
import pandas as pd
import requests

app = Flask(__name__)

weather_stats_API = {"air_temp": "https://api-open.data.gov.sg/v2/real-time/api/air-temperature",
                    "wind_speed": "https://api-open.data.gov.sg/v2/real-time/api/wind-speed",
                    "wind_direction" : "https://api-open.data.gov.sg/v2/real-time/api/wind-direction", # readings are in degrees, ie 315 degree --> Northwest
                    "relative_humidity" : "https://api-open.data.gov.sg/v2/real-time/api/relative-humidity",
                    "2_hr_weather": "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast", # res --> string ("cloudy, rainy")
                    "uv_index" : "https://api-open.data.gov.sg/v2/real-time/api/uv",
                    "heat_stress" : "https://api-open.data.gov.sg/v2/real-time/api/weather?api=wbgt"
                    }

# Relevant User Details
current_date = "2024-03-20"
current_datetime = "2025-03-20T15:00:00"
location = "Yishun"

def windDirection_mapping(uv):
    # source: https://gist.github.com/theKAKAN/b40bf54144a6eb90313ad00681e3fbcc
    directions = ["N","NNE","NE","ENE","E",
                    "ESE", "SE", "SSE","S",
                    "SSW","SW","WSW","W",
                    "WNW","NW","NNW" ]
    dir = []
    for i in range(len(uv)):
        angle = uv[i]
        section = int(angle/22.5)
        dir.append(directions[section])
    return dir

def get_weather_data(api, datetime):

    # air temp, wind speed, wind direction, relative humidity
    request = api["air_temp"] + "?date=" + datetime
    response = requests.get(request).json()
    print(request)

    # locations
    stations = response["data"]["stations"]
    loc_df = pd.json_normalize(stations).rename(columns={'location.latitude': 'lat', 'location.longitude': 'lon', 'name':'location', 'id':'stationId'})
    loc_df.drop(columns=["deviceId"], inplace=True)

    # air temp
    data = response["data"]["readings"][0]["data"]
    airTemp_df = pd.json_normalize(data).rename(columns={'value':'airTemp'})

    # wind speed
    request2 = api["wind_speed"] + "?date=" + datetime
    response2 = requests.get(request2).json()
    windSpeed_df = pd.json_normalize(response2["data"]["readings"][0]["data"]).rename(columns={'value':'windSpeed'})

    # wind direction
    request3 = api["wind_direction"] + "?date=" + datetime
    response3 = requests.get(request3).json()
    windDirection_df = pd.json_normalize(response3["data"]["readings"][0]["data"]).rename(columns={'value':'windDirection_deg'})

    # relative humidity
    request4 = api["relative_humidity"] + "?date=" + datetime
    response4 = requests.get(request4).json()
    humidity_df = pd.json_normalize(response4["data"]["readings"][0]["data"]).rename(columns={'value':'humidity'})

    df = loc_df.set_index('stationId').join([airTemp_df.set_index('stationId'), windSpeed_df.set_index('stationId'), windDirection_df.set_index('stationId'), humidity_df.set_index('stationId')],how='inner').reset_index()
    df['windDirection_dir'] = windDirection_mapping(df["windDirection_deg"])

    return df.to_json()

@app.route("/")
def home():
    return render_template("index.html")  # Looks inside /templates/

@app.route("/api/weather")
def weather_api():
    data = get_weather_data(weather_stats_API, current_datetime)
    return data


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)