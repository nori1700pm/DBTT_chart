from datetime import datetime
import pandas as pd
import pickle
import requests
from sklearn.preprocessing import MinMaxScaler
from dotenv import load_dotenv
from geopy.distance import geodesic
import numpy as np
from scipy.stats import percentileofscore
# from api import 
# import api
from analytics.api import get_weather_data


class Data:
    def __init__(self):
        print("Data initialized")
        # Get today's date in the format 'YYYY-MM-DD'
        # today_date = datetime.now().strftime("%Y-%m-%d")
        DATA = pd.read_csv("data/weather_data_5years.csv")
        # # Filter out rows where the date matches today's date (ignoring time)
        # DATA = DATA[~DATA["date"].str.startswith(today_date)]
        # Split the 'date' column into 'date' and 'time'
        DATA[["date", "time"]] = DATA["date"].str.split("T", expand=True)
        DATA = self.process_weather_data(DATA, True)
        DATA.rename(columns={"lon": "longitude", "lat": "latitude"}, inplace=True)
        self.DATA = DATA
        self.CONFIG = load_dotenv(".env")

    def process_weather_data(self, df: pd.DataFrame, historical: bool) -> pd.DataFrame:
        """
        Normalizes weather data and computes heat score.

        Parameters:
        df (pd.DataFrame): DataFrame containing weather data with columns 'airTemp', 'humidity', and 'windSpeed'.

        Returns:
            pd.DataFrame: DataFrame with additional columns 'airTemp_norm', 'humidity_norm', 'windSpeed_norm', and 'heat_score'.
        """
        if historical:
            # Extract year, month, and day from the 'date' column
            self.scaler = MinMaxScaler()
            self.scaler_heat = MinMaxScaler()

            # Normalize temperature, humidity, and wind speed (scaling to 0-1)
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = (
                scaler.fit_transform(df[["airTemp", "humidity", "windSpeed"]])
            )

            # Compute heat index score (higher means hotter perception)
            df["heat_score"] = (
                df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
            )
            df["heat_score_norm"] = scaler_heat.fit_transform(df[["heat_score"]])

            # with open("scalers.pkl", "wb") as f:
            #     pickle.dump((scaler, scaler_heat), f)

        else:
            # with open("scalers.pkl", "rb") as f:
            #     scaler, scaler_heat = pickle.load(f)
            scaler = self.scaler
            scaler_heat = self.scaler_heat

            # Transform using the same scaler fitted on historical data
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = scaler.transform(
                df[["airTemp", "humidity", "windSpeed"]]
            )

            # Compute heat score
            df["heat_score"] = (
                df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
            )

            # Normalize heat score using the same heat_score scaler
            df["heat_score_norm"] = scaler_heat.transform(df[["heat_score"]])

        return df

    def get_data(self):
        return self.DATA

    def get_current_weather(self, mock: bool = False) -> pd.DataFrame:
        """
        Fetches the current weather data.

        Returns:
            pd.DataFrame: DataFrame containing the current weather data.
        """
        datetime_now = datetime.now()
        datetime_str = self.date_to_str(datetime_now)
        weather_data = get_weather_data(datetime_str)
        weather_data.rename(
            columns={"lat": "latitude", "lon": "longitude"}, inplace=True
        )
        if mock:
            weather_data.loc[weather_data["stationId"] == "S50", "airTemp"] = 33
        weather_data = self.process_weather_data(weather_data, False)
        return weather_data

    def date_to_str(self, date_obj: datetime) -> str:
        """
        Converts a datetime object to a string in the required format.

        Parameters:
            date_obj (datetime): The datetime object to convert.

        Returns:
            str: The formatted date string.
        """
        date_str = date_obj.strftime("%Y-%m-%dT%H:%M:%S")
        return date_str

    def postal_code_to_latlong(self, postal_code: str) -> tuple[float, float] | None:
        """
        Converts a postal code to latitude and longitude.

        Parameters:
            postal_code (str): The postal code to convert.

        Returns:
            tuple: A tuple containing the latitude and longitude, or None if not found.
        """

        postal_code = str(postal_code)
        KEY = self.CONFIG["ONEMAPS_KEY"]
        url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal_code}&returnGeom=Y&getAddrDetails=N&pageNum=1"
        headers = {"Authorization": f"Bearer {KEY}"}
        response = requests.get(url, headers=headers)

        data = response.json()
        # print(data)
        if data["found"] > 0:
            try:
                lat = float(data["results"][0]["LATITUDE"])
                lon = float(data["results"][0]["LONGITUDE"])
                return lat, lon
            except:
                pass

        return None

    def find_nearest_stations(
        self, df: pd.DataFrame, num_stations: int = 1
    ) -> pd.DataFrame:
        """
        Finds the nearest weather stations to the given location.

        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with columns 'latitude' and 'longitude'.
            num_stations (int): Number of nearest stations to find. Default is 1.

        Returns:
            pd.DataFrame: DataFrame containing the nearest weather stations sorted by distance.
        """

        self.compute_distance(self.LAT, self.LON, df)
        nearest_stations = df.nsmallest(num_stations, "distance")
        nearest_stations = self.compute_weights(nearest_stations)

        return nearest_stations

    def compute_distance(
        self, df: pd.DataFrame
    ) -> pd.DataFrame:
        df["distance"] = df.apply(
            lambda row: geodesic(
                (self.LAT, self.LON), (row["latitude"], row["longitude"])
            ).km,
            axis=1,
        )
        return df

    def compute_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        df["distance_weight"] = 1 / df["distance"]
        df["distance_weight"] = df["distance_weight"] / df["distance_weight"].sum()
        return df

    def filter_data(
        self, df: pd.DataFrame, nearest_stations: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Filters the historical data based on the nearest weather stations.

        Parameters:
            df (pd.DataFrame): DataFrame containing historical weather data.
            nearest_stations (pd.DataFrame): DataFrame containing the nearest weather stations.

        Returns:
            pd.DataFrame: Filtered DataFrame containing historical data for the nearest stations.
        """
        filtered_data = df[df["stationId"].isin(nearest_stations["stationId"])]
        return filtered_data

    def compute_weighted_heat_score(self, df: pd.DataFrame) -> float:
        """
        Computes weighted heat score based on the nearest weather stations.

        Parameters:
            df (pd.DataFrame): DataFrame containing weather data for locations nearest to user.

        Returns:
            float: The weighted heat score based on the nearest weather stations.
        """

        # Compute weighted heat score
        weighted_heat_score = np.dot(df["distance_weight"], df["heat_score_norm"])
        return weighted_heat_score

    def find_threshold(self, historical_data, percentile_threshold):
        THRESHOLD = np.percentile(
            historical_data["weighted_heat_score"], percentile_threshold
        )
        return THRESHOLD

    def is_hotspot(
        self, df, historical_data, percentile_threshold=90
    ):
        """Determines if a location is a heat hotspot based on weighted heat score"""

        nearest_stations = self.find_nearest_stations(
            self.LAT, self.LON, df, num_stations=3
        )  # Find 3 nearest stations
        print("Nearest Stations:")
        print(nearest_stations)

        weighted_score = self.compute_weighted_heat_score(nearest_stations)

        # cached_data = pd.read_csv("data/location_data.csv")
        # match_date = cached_data["date"] == datetime.now().strftime("%Y-%m-%d")
        # match_lat = cached_data["latitude"] == self.LAT
        # match_lon = cached_data["longitude"] == self.LON
        # if match_date.any() and match_lat.any() and match_lon.any():
        #     result = cached_data.loc[match_date & match_lat & match_lon, ["threshold", "percentile"]]
        #     heat_threshold = result["threshold"].values[0]
        #     percentile = result["percentile"].values[0]
        #     return weighted_score > heat_threshold, weighted_score, heat_threshold, percentile

        historical_data = self.filter_data(
            historical_data, nearest_stations
        )  # Filter historical data based on nearest stations

        historical_data = self.compute_distance(self.LAT, self.LON, historical_data)

        def weighted_heat_score(group):
            # group = compute_distance(self.LAT, self.LON, group)
            # Compute weighted heat score for each day
            group = self.compute_weights(group)
            return self.compute_weighted_heat_score(group)

        historical_data = (
            historical_data.groupby(["date"])
            .apply(weighted_heat_score, include_groups=False)
            .reset_index(name="weighted_heat_score")
        )

        # print(f"Time for filtering: {timings[1] - timings[0]:.2f}s")
        # print(f"Time for computing weighted heat scores: {timings[2] - timings[1]:.2f}s")
        # print(f"Time for computing weighted heat scores: {timings[3] - timings[2]:.2f}s")
        # print(f"Total Processing Time: {timings[-1] - timings[0]:.2f}s")
        # display(historical_data)
        # Compute threshold (90th percentile of heat scores in dataset)

        heat_threshold = self.find_threshold(historical_data, percentile_threshold)
        percentile = percentileofscore(
            historical_data["weighted_heat_score"], weighted_score
        )

        # with open("data/location_data.csv", "a") as f:
        #     date_str = datetime.now().strftime("%Y-%m-%d")
        #     f.write(f"{date_str},{self.LAT},{self.LON},{heat_threshold},{percentile}\n")

        # print(weighted_score > heat_threshold, weighted_score, heat_threshold, percentile)
        return (
            weighted_score > heat_threshold,
            weighted_score,
            heat_threshold,
            percentile,
        )
        
    def set_location(self, postal_code):
        self.LAT, self.LON = self.postal_code_to_latlong(postal_code)
        


# WEATHER = get_current_weather(mock=False)
# display(WEATHER)
# LAT, LON = postal_code_to_latlong(POSTAL_CODE)
# NEAREST = find_nearest_stations(LAT, LON, WEATHER, num_stations=3)
# isHotspot, score, threshold, percentile = is_hotspot(
#     LAT, LON, WEATHER, HISTORICAL, percentile_threshold=80
# )
# # display(is_hotspot(LAT, LON, WEATHER, HISTORICAL, percentile_threshold=70))
# print(f"Is Heatwave: {isHotspot}")
# print(f"Weighted Score: {score:.3f}")
# print(f"Threshold: {threshold:.3f}")
# print(f"Percentile: {percentile:.3f}")
