import os
import numpy as np
import pandas as pd
import requests
from datetime import datetime, timedelta
from dotenv import dotenv_values
from geopy.distance import geodesic
from sklearn.preprocessing import MinMaxScaler
from scipy.stats import percentileofscore

from analytics.api import get_weather_data
from analytics.api import INDOOR_MAPPING 


class WeatherAnalyzer:
    """WeatherAnalyzer is a class designed to analyze weather data and provide heat-related insights.
    It processes historical and current weather data, computes heat scores, and determines if a
    location is a heat hotspot based on weighted heat scores and thresholds.
    Attributes:
        CONFIG (dict): Configuration values loaded from the environment file.
        scaler (MinMaxScaler): Scaler for normalizing air temperature, humidity, and wind speed.
        scaler_heat (MinMaxScaler): Scaler for normalizing heat scores.
        DATA (pd.DataFrame): Processed historical weather data.
        CURRENT (pd.DataFrame): Cached current weather data.
        date (datetime): Timestamp of the last fetched current weather data.
    Methods:
        __init__(): Initializes the WeatherAnalyzer instance, loads configurations, processes historical data, and fetches current weather.
        _load_and_process_historical_data(): Loads and processes historical weather data from a CSV file.
        _process_weather_data(df, historical): Normalizes weather data and computes heat scores.
        get_current_weather(mock): Fetches the current weather data, with an option to mock data for testing.
        _date_to_str(date_obj): Converts a datetime object to a formatted string.
        postal_code_to_latlong(postal_code): Converts a postal code to latitude and longitude using the OneMap API.
        find_nearest_stations(latitude, longitude, num_stations): Finds the nearest weather stations to a given location.
        __compute_distance(df, latitude, longitude): Computes the geodesic distance between a location and weather stations.
        __compute_weights(df): Computes weights for weather stations based on their distance.
        __compute_weighted_heat_score(df): Computes the weighted heat score for a set of weather stations.
        find_threshold(historical_data, percentile_threshold): Determines the heat score threshold based on historical data and a percentile.
        is_hotspot(nearest_stations, latitude, longitude, percentile_threshold): Determines if a location is a heat hotspot based on weighted heat scores.
        __filter_data(nearest_stations): Filters historical data to include only records from the nearest weather stations.
    """

    def __init__(self, config: dict = None):
        """
        Initializes the WeatherAnalyzer instance.
        Loads configuration, processes historical weather data, and initializes scalers.
        """
        print("WeatherAnalyzer initialized")
        self.CONFIG = dotenv_values(".env")
        self.scaler = MinMaxScaler()
        self.scaler_heat = MinMaxScaler()
        self.DATA = self._load_and_process_historical_data()
        self.CURRENT = None
        self.date = datetime.now()
        self.CURRENT = self.get_current_weather()
        self.CONFIG = config

    def _load_and_process_historical_data(self) -> pd.DataFrame:
        """
        Loads and processes historical weather data.
        Returns:
            pd.DataFrame: Processed historical weather data.
        """
        base_path = os.path.dirname(__file__)  # gets the directory of weather_service.py
        file_path = os.path.join(base_path, 'data', 'weather_data_5years.csv')
        DATA = pd.read_csv(file_path)
        DATA[["date", "time"]] = DATA["date"].str.split("T", expand=True)
        DATA.rename(columns={"lon": "longitude", "lat": "latitude"}, inplace=True)
        return self._process_weather_data(DATA, historical=True)

    def _process_weather_data(self, df: pd.DataFrame, historical: bool) -> pd.DataFrame:
        """
        Normalizes weather data and computes heat score.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with columns 'airTemp', 'humidity', and 'windSpeed'.
            historical (bool): Whether the data is historical or current.
        Returns:
            pd.DataFrame: DataFrame with additional normalized and computed columns.
        """
        if historical:
            # self.scaler.fit(df[["airTemp", "humidity", "windSpeed"]])
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = (
                self.scaler.fit_transform(df[["airTemp", "humidity", "windSpeed"]])
            )
            df["heat_score"] = (
                df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
            )
            # self.scaler_heat.fit(df[["heat_score"]])
            df["heat_score_norm"] = self.scaler_heat.fit_transform(df[["heat_score"]])

        else:
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = (
                self.scaler.transform(df[["airTemp", "humidity", "windSpeed"]])
            )
            df["heat_score"] = (
                df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
            )
            df["heat_score_norm"] = self.scaler_heat.transform(df[["heat_score"]])

        return df

    def get_current_weather(self, mock: bool = False) -> pd.DataFrame:
        """
        Fetches the current weather data.
        Parameters:
            mock (bool): Whether to mock the data for testing purposes.
        Returns:
            pd.DataFrame: DataFrame containing the current weather data.
        """
        datetime_now = datetime.now()
        if self.CURRENT is None or self.date - datetime_now > timedelta(minutes=5):
            datetime_str = self._date_to_str(datetime_now)
            weather_data = get_weather_data(datetime_str)
            weather_data.rename(
                columns={"lat": "latitude", "lon": "longitude"}, inplace=True
            )
            if mock:
                weather_data.loc[weather_data["stationId"] == "S50", "airTemp"] = 33
            self.CURRENT = self._process_weather_data(weather_data, historical=False)

        return self.CURRENT

    def _date_to_str(self, date_obj: datetime) -> str:
        """
        Converts a datetime object to a string in the required format.
        Parameters:
            date_obj (datetime): The datetime object to convert.
        Returns:
            str: The formatted date string.
        """
        return date_obj.strftime("%Y-%m-%dT%H:%M:%S")

    
    def get_forecast_df(self, location: str = None) -> pd.DataFrame:
        url = self.CONFIG["2_hr_weather"] + "?date=" + self.CONFIG["CURRENT_DATETIME"]
        response = requests.get(url).json()

        area_metadata = pd.json_normalize(response["data"]["area_metadata"])
        forecasts = pd.json_normalize(response["data"]["items"][0]["forecasts"])

        area_metadata = area_metadata.rename(columns={
            "name": "name",
            "label_location.latitude": "lat",
            "label_location.longitude": "lon"
        })
        forecasts = forecasts.rename(columns={"area": "name", "forecast": "forecast"})

        df = pd.merge(area_metadata, forecasts, on="name", how="inner")
        
        if location:
            df = df[df["name"] == location]
        
        return df
    
    def get_indoor_summary(self) -> pd.DataFrame:
        # Reverse map: stationId → room
        station_to_room = {v: k for k, v in INDOOR_MAPPING.items()}

        # Copy and map
        df = self.CURRENT.copy()
        df["room"] = df["stationId"].map(station_to_room)

        # Keep only rows where room is mapped (not NaN)
        df = df[df["room"].notna()]

        # Get Living Room's wind direction 
        living_room_dir = df[df["room"] == "Living Room"]["windDirection_dir"].values
        wind_dir = living_room_dir[0] if len(living_room_dir) > 0 else None

        # Replace all wind directions with Living Room's wind dir
        df["windDirection_dir"] = wind_dir

        # Uses panda vectorizer to loop through each row
        df["heatStress"] = (
            0.726330 * df["airTemp"] +
            0.012713 * df["windSpeed"] +
            0.109697 * df["humidity"] -
            5.12977
        ).round(3)

        # Select only required columns
        final_df = df[["room", "airTemp", "humidity", "windSpeed", "windDirection_dir", "heatStress"]].reset_index(drop=True)

        return final_df
    
    def postal_code_to_latlong(
        self, postal_code: str | int
    ) -> tuple[float, float] | None:
        """
        Converts a postal code to latitude and longitude using the OneMap API.
        Parameters:
            postal_code (str): The postal code to convert.
        Returns:
            tuple: A tuple containing the latitude and longitude, or None if not found.
        """
        KEY = self.CONFIG["ONEMAPS_KEY"]
        url = f"https://www.onemap.gov.sg/api/common/elastic/search?searchVal={postal_code}&returnGeom=Y&getAddrDetails=N&pageNum=1"
        headers = {"Authorization": f"Bearer {KEY}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        if data["found"] > 0:
            try:
                lat = float(data["results"][0]["LATITUDE"])
                lon = float(data["results"][0]["LONGITUDE"])
                return lat, lon
            except Exception as e:
                print(f"Error processing postal code {postal_code}: {e}")
        return None

    def find_nearest_stations(
        self, latitude, longitude, num_stations: int = 1
    ) -> pd.DataFrame:
        """
        Finds the nearest weather stations to the specified location.
        This method calculates the distance between the given latitude and longitude
        and the weather stations in the dataset, then identifies the nearest stations
        based on the specified number.
        Parameters:
            latitude (float): Latitude of the target location.
            longitude (float): Longitude of the target location.
            num_stations (int, optional): Number of nearest stations to find. Default is 1.
            pd.DataFrame: A DataFrame containing the nearest weather stations, sorted by
            distance, with computed weights for each station.
        Returns:
            pd.DataFrame: DataFrame containing the nearest weather stations sorted by distance.
        """
        nearest = self.get_current_weather().copy(deep=True)
        nearest = self.__compute_distance(nearest, latitude, longitude)
        nearest_stations = nearest.nsmallest(num_stations, "distance")
        return self.__compute_weights(nearest_stations)

    def __compute_distance(
        self, df: pd.DataFrame, latitude: float, longitude: float
    ) -> pd.DataFrame:
        """
        Computes the geodesic distance between the user's location and each station.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with columns 'latitude' and 'longitude'.
        Returns:
            pd.DataFrame: DataFrame with an additional 'distance' column.
        """
        df["distance"] = df.apply(
            lambda row: geodesic(
                (latitude, longitude), (row["latitude"], row["longitude"])
            ).km,
            axis=1,
        )
        return df

    def __compute_weights(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes the weight for each station based on its distance.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with a 'distance' column.
        Returns:
            pd.DataFrame: DataFrame with an additional 'distance_weight' column.
        """
        df["distance_weight"] = 1 / df["distance"]
        df["distance_weight"] /= df["distance_weight"].sum()
        return df

    def __compute_weighted_heat_score(self, df: pd.DataFrame) -> float:
        """
        Computes the weighted heat score based on the nearest weather stations.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data for locations nearest to the user.
        Returns:
            float: The weighted heat score.
        """
        return np.dot(df["distance_weight"], df["heat_score_norm"])

    def find_threshold(
        self, historical_data: pd.DataFrame, percentile_threshold: int
    ) -> float:
        """
        Finds the threshold value for heat scores based on historical data.
        Parameters:
            historical_data (pd.DataFrame): DataFrame containing historical weather data.
            percentile_threshold (int): Percentile threshold for determining the heat score threshold.
        Returns:
            float: The threshold value for heat scores.
        """
        return np.percentile(
            historical_data["weighted_heat_score"], percentile_threshold
        )

    def is_hotspot(
        self,
        nearest_stations: pd.DataFrame,
        latitude: float,
        longitude: float,
        percentile_threshold: int = 90,
    ) -> dict:
        """
        Determines if a location is a heat hotspot based on weighted heat score.
        Parameters:
            df (pd.DataFrame): DataFrame containing current weather data.
            historical_data (pd.DataFrame): DataFrame containing historical weather data.
            percentile_threshold (int): Percentile threshold for determining the heat score threshold.
        Returns:
            tuple: A tuple containing:
                - isHotspot (bool): Whether the location is a heat hotspot.
                - weighted_score (float): The weighted heat score.
                - heat_threshold (float): The heat score threshold.
                - percentile (float): The percentile of the weighted heat score.
        """
        weighted_score = self.__compute_weighted_heat_score(nearest_stations)

        historical_data = self.__filter_data(nearest_stations)
        historical_data = self.__compute_distance(historical_data, latitude, longitude)

        def weighted_heat_score(group):
            group = self.__compute_weights(group)
            return self.__compute_weighted_heat_score(group)

        historical_data = (
            historical_data.groupby(["date"])
            .apply(weighted_heat_score, include_groups=False)
            .reset_index(name="weighted_heat_score")
        )

        heat_threshold = self.find_threshold(historical_data, percentile_threshold)
        percentile = percentileofscore(
            historical_data["weighted_heat_score"], weighted_score
        )

        return {
            "isHotspot": bool(weighted_score > heat_threshold),
            "weighted_score": weighted_score,
            "heat_threshold": heat_threshold,
            "percentile": percentile,
        }

    def __filter_data(self, nearest_stations: pd.DataFrame) -> pd.DataFrame:
        """
        Filters historical data based on the nearest weather stations.
        Parameters:
            df (pd.DataFrame): DataFrame containing historical weather data.
            nearest_stations (pd.DataFrame): DataFrame containing the nearest weather stations.
        Returns:
            pd.DataFrame: Filtered DataFrame containing historical data for the nearest stations.
        """
        return self.DATA[self.DATA["stationId"].isin(nearest_stations["stationId"])]

    def angle_to_dir(self, angle: int):
        """Converts an angle in degrees to a compass direction.
        Parameters:
            angle (int): The angle in degrees."""
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
        angle = angle % 360
        section = int(angle / 22.5)
        return directions[section]
