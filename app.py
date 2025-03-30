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




@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 404


@app.route("/")
def home():
    return render_template("index.html")  # Looks inside /templates/


@app.route("/api/indoor_wbgt")
def indoor_wbgt():
    room = request.args.get("room")
    if not room:
        abort(400, description="Missing room name")

    try:
        df = weather_service.get_indoor_summary(room)
        return df.to_json(orient="records")
    except ValueError as e:
        abort(400, description=str(e))


@app.route("/api/weather/history")
def weather_history():
    data = weather_service.DATA
    data = data.sample(100)
    return data.to_json(orient="records")


@app.route("/api/weather/current")
def weather_current():
    return weather_service.get_indoor_summary().to_json(orient="records")


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
