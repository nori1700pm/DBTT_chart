import requests
import pandas as pd

API = {
    "air_temp": "https://api-open.data.gov.sg/v2/real-time/api/air-temperature",
    "wind_speed": "https://api-open.data.gov.sg/v2/real-time/api/wind-speed",
    "wind_direction": "https://api-open.data.gov.sg/v2/real-time/api/wind-direction",  # readings are in degrees, ie 315 degree --> Northwest
    "relative_humidity": "https://api-open.data.gov.sg/v2/real-time/api/relative-humidity",
    "2_hr_weather": "https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast",  # res --> string ("cloudy, rainy")
    "uv_index": "https://api-open.data.gov.sg/v2/real-time/api/uv",
    "heat_stress": "https://api-open.data.gov.sg/v2/real-time/api/weather?api=wbgt",
}


INDOOR_MAPPING = {
    "Living Room": "S109",  # Ang Mo Kio Avenue 5
    "Bedroom": "S44",  # Nanyang Avenue
    "Kitchen": "S106",  # Pulau Ubin
    "Shelter": "S117",  # Banyan Road
    "Storage": "S43",  # Kim Chuan Road
    "Toilet": "S107",  # East Cost Parkway
}


def get_weather_data(datetime, api=API) -> pd.DataFrame:

    # air temp, wind speed, wind direction, relative humidity
    request = api["air_temp"] + "?date=" + datetime
    response = requests.get(request).json()

    # locations
    stations = response["data"]["stations"]
    loc_df = pd.json_normalize(stations).rename(
        columns={
            "location.latitude": "lat",
            "location.longitude": "lon",
            "name": "location",
            "id": "stationId",
        }
    )
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
    windDirection_df = pd.json_normalize(
        response3["data"]["readings"][0]["data"]
    ).rename(columns={"value": "windDirection_deg"})

    # relative humidity
    request4 = api["relative_humidity"] + "?date=" + datetime
    response4 = requests.get(request4).json()
    humidity_df = pd.json_normalize(response4["data"]["readings"][0]["data"]).rename(
        columns={"value": "humidity"}
    )

    # uv index
    # check if time is in between 7am to 9pm
    uv_index = 0
    if datetime[11:13] >= "07" and datetime[11:13] <= "21":
        request5 = api["uv_index"] + "?date=" + datetime
        response5 = requests.get(request5).json()
        uv_index = response5["data"]["records"][0]["index"][0]["value"]

    df = (
        loc_df.set_index("stationId")
        .join(
            [
                airTemp_df.set_index("stationId"),
                windSpeed_df.set_index("stationId"),
                windDirection_df.set_index("stationId"),
                humidity_df.set_index("stationId"),
            ],
            how="inner",
        )
        .reset_index()
    )
    df["windDirection_dir"] = windDirection_mapping(df["windDirection_deg"])
    df["uv_index"] = uv_index

    return df


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
