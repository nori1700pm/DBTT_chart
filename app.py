from flask import Flask, render_template, jsonify, request, abort, Response
import pandas as pd
import requests
import json
from analytics.weather_service import WeatherAnalyzer
from analytics.AI import AI
from dotenv import dotenv_values

CONFIG = dotenv_values(".env")
weather_service = WeatherAnalyzer(CONFIG)
ai_service = AI(CONFIG)
app = Flask(__name__)
app.config['JSON_SORT_KEYS'] = False


weather_stats_API = {
    "air_temp": "https://api-open.data.gov.sg/v2/real-time/api/air-temperature",
    "wind_speed": "https://api-open.data.gov.sg/v2/real-time/api/wind-speed",
    "wind_direction": "https://api-open.data.gov.sg/v2/real-time/api/wind-direction",  # readings are in degrees, ie 315 degree --> Northwest
    "relative_humidity": "https://api-open.data.gov.sg/v2/real-time/api/relative-humidity",
    "2_hr_weather": "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast",  # res --> string ("cloudy, rainy")
    "uv_index": "https://api-open.data.gov.sg/v2/real-time/api/uv",
    "heat_stress": "https://api-open.data.gov.sg/v2/real-time/api/weather?api=wbgt",
}

# Relevant User Details
current_date = "2024-03-20"
current_datetime = "2025-03-20T15:00:00"
location = "Yishun"


def windDirection_mapping(uv):
    # source: https://gist.github.com/theKAKAN/b40bf54144a6eb90313ad00681e3fbcc
    directions = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    dir = []
    for i in range(len(uv)):
        angle = uv[i]
        section = int(angle / 22.5)
        dir.append(directions[section])
    return dir


def uv_mapping(uv):
    if uv <= 2:
        return "Low", "Feel free to go out and play!"
    elif 3 <= uv <= 5:
        return "Moderate", "Use sunscreen (at least SPF 30) and sunglasses."
    elif 6 <= uv <= 7:
        return "High", "Stay in shade during midday."
    elif 8 <= uv <= 10:
        return "Very High", "Reduce time in the sun!"
    else:
        return "Extreme", "Avoid being outside!"


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
    airTemp_df = pd.json_normalize(data).rename(columns={"value": "airTemp"})

    # wind speed
    request2 = api["wind_speed"] + "?date=" + datetime
    response2 = requests.get(request2).json()
    windSpeed_df = pd.json_normalize(response2["data"]["readings"][0]["data"]).rename(
        columns={"value": "windSpeed"}
    )

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


@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 404


@app.route("/")
def home():
    return render_template("index.html")  # Looks inside /templates/


@app.route("/api/weather")
def weather_api():
    data = get_weather_data(weather_stats_API, current_datetime)
    return data


# @app.route("/api/heat_stress")
# def weather_api():
#     data = get_weather_data(weather_stats_API, current_datetime)
#     return data


@app.route("/api/2hr_forecast")
def forecase_api():
    request = weather_stats_API["2_hr_weather"] + "?date=" + current_datetime
    response = requests.get(request).json()

    locations = response["data"]["area_metadata"]
    loc_df = pd.json_normalize(locations).rename(columns={'label_location.latitude': 'lat', 'label_location.longitude': 'lon'})
    
    forecast_data = response["data"]["items"][0]["forecasts"]
    forecast_df = pd.json_normalize(forecast_data).rename(columns={'area': 'name', 'forecast': 'forecast'})

    combined_df = pd.merge(loc_df, forecast_df, on='name', how='inner')
    combined_df = combined_df[combined_df['name'] == location]    

    # Optional filter by query parameter
    # location_param = request.args.get('location')  # e.g., /api/2hr_forecast?location=Bedok
    # if location_param:
    #     combined_df = combined_df[combined_df['name'] == location_param]

    return combined_df.to_json()


@app.route("/api/uv_index")
def uv_index_api():
    request = weather_stats_API["uv_index"] + "?date=" + current_datetime
    response = requests.get(request).json()

    print(request)

    uvIndex_df = pd.json_normalize(response["data"]["records"][0]["index"])

    # Apply the mapping to create a new advice column
    uvIndex_df[["level", "advice"]] = uvIndex_df["value"].apply(
        lambda x: pd.Series(uv_mapping(x))
    )

    return uvIndex_df.to_json()


@app.route("/api/weather/history")
def weather_history():
    data = weather_service.DATA
    data = data.sample(100)
    return data.to_json(orient="records")


@app.route("/api/weather/current")
def weather_current():
    return weather_service.get_current_weather().to_json(orient="records")


@app.route("/api/weather/user/nearest")
def get_nearest_data():
    CODE = request.args.get("postal_code")
    if not CODE:
        abort(400, description="Postal code is required")
    latitude, longitude = weather_service.postal_code_to_latlong(CODE)
    nearest = weather_service.find_nearest_stations(latitude, longitude, num_stations=3)
    return nearest.to_json(orient="records")


@app.route("/api/weather/user/analysis")
def perform_analysis(CODE: str | int = None):
    CODE = CODE or request.args.get("postal_code")
    if not CODE:
        abort(400, description="Postal code is required")
    latitude, longitude = weather_service.postal_code_to_latlong(CODE)
    nearest = weather_service.find_nearest_stations(latitude, longitude, num_stations=3)
    hotspot_data = weather_service.is_hotspot(nearest, latitude, longitude)
    hotspot_data["weather_station_data"] = nearest.to_dict(orient="records")
    return json.dumps(hotspot_data, indent=4)

@app.route("/api/ai/suggestions")
def get_suggestions():
    print("suggestions retreival")
    CODE = request.args.get("postal_code")
    DIR = request.args.get("direction")
    if not CODE:
        abort(400, description="Postal code is required")
    if not DIR:
        abort(400, description="House direction is required")
    
    DIR = weather_service.angle_to_dir(int(DIR))
    hotspot_data = {"house_orientation": DIR}
    hotspot_data.update(json.loads(perform_analysis(CODE)))
    suggestions = ai_service.generate_suggestions(hotspot_data)
    # return suggestions
    return jsonify({"suggestion": suggestions, "data": hotspot_data})

@app.route("/test")
def test():
    print(weather_service.date)
    return weather_service.get_current_weather().to_json(orient="records")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
