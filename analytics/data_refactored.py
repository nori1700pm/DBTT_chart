from datetime import datetime, timedelta
import pandas as pd
import pickle
import requests
from sklearn.preprocessing import MinMaxScaler
from dotenv import load_dotenv
from geopy.distance import geodesic
import numpy as np
from scipy.stats import percentileofscore
from analytics.api import get_weather_data


class WeatherAnalyzer:
    """
    A class to analyze weather data and determine heat-related insights.
    """

    def __init__(self):
        """
        Initializes the WeatherAnalyzer instance.
        Loads configuration, processes historical weather data, and initializes scalers.
        """
        print("WeatherAnalyzer initialized")
        self.CONFIG = load_dotenv(".env")
        self.scaler = MinMaxScaler()
        self.scaler_heat = MinMaxScaler()
        self.DATA = self._load_and_process_historical_data()
        self.CURRENT = None
        self.date = datetime.now()
        self.CURRENT = self.get_current_weather()

    def _load_and_process_historical_data(self) -> pd.DataFrame:
        """
        Loads and processes historical weather data.
        Returns:
            pd.DataFrame: Processed historical weather data.
        """
        DATA = pd.read_csv("data/weather_data_5years.csv")
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
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = self.scaler.fit_transform(
                df[["airTemp", "humidity", "windSpeed"]]
            )
            df["heat_score"] = df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
            # self.scaler_heat.fit(df[["heat_score"]])
            df["heat_score_norm"] = self.scaler_heat.fit_transform(df[["heat_score"]])
            
        else: 
            df[["airTemp_norm", "humidity_norm", "windSpeed_norm"]] = self.scaler.transform(
                df[["airTemp", "humidity", "windSpeed"]]
            )
            df["heat_score"] = df["airTemp_norm"] + df["humidity_norm"] - df["windSpeed_norm"]
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
            weather_data.rename(columns={"lat": "latitude", "lon": "longitude"}, inplace=True)
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

    def postal_code_to_latlong(self, postal_code: str) -> tuple[float, float] | None:
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

    def find_nearest_stations(self, df: pd.DataFrame, num_stations: int = 1) -> pd.DataFrame:
        """
        Finds the nearest weather stations to the user's location.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with columns 'latitude' and 'longitude'.
            num_stations (int): Number of nearest stations to find. Default is 1.
        Returns:
            pd.DataFrame: DataFrame containing the nearest weather stations sorted by distance.
        """
        df = self.__compute_distance(df)
        nearest_stations = df.nsmallest(num_stations, "distance")
        return self.__compute_weights(nearest_stations)

    def __compute_distance(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Computes the geodesic distance between the user's location and each station.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data with columns 'latitude' and 'longitude'.
        Returns:
            pd.DataFrame: DataFrame with an additional 'distance' column.
        """
        df["distance"] = df.apply(
            lambda row: geodesic((self.LAT, self.LON), (row["latitude"], row["longitude"])).km,
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

    def compute_weighted_heat_score(self, df: pd.DataFrame) -> float:
        """
        Computes the weighted heat score based on the nearest weather stations.
        Parameters:
            df (pd.DataFrame): DataFrame containing weather data for locations nearest to the user.
        Returns:
            float: The weighted heat score.
        """
        return np.dot(df["distance_weight"], df["heat_score_norm"])

    def find_threshold(self, historical_data: pd.DataFrame, percentile_threshold: int) -> float:
        """
        Finds the threshold value for heat scores based on historical data.
        Parameters:
            historical_data (pd.DataFrame): DataFrame containing historical weather data.
            percentile_threshold (int): Percentile threshold for determining the heat score threshold.
        Returns:
            float: The threshold value for heat scores.
        """
        return np.percentile(historical_data["weighted_heat_score"], percentile_threshold)

    def is_hotspot(self, df: pd.DataFrame, percentile_threshold: int = 90) -> tuple:
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
        nearest_stations = self.find_nearest_stations(df, num_stations=3)
        weighted_score = self.compute_weighted_heat_score(nearest_stations)

        historical_data = self.filter_data(nearest_stations)
        historical_data = self.__compute_distance(historical_data)

        def weighted_heat_score(group):
            group = self.__compute_weights(group)
            return self.compute_weighted_heat_score(group)

        historical_data = (
            historical_data.groupby(["date"])
            .apply(weighted_heat_score, include_groups=False)
            .reset_index(name="weighted_heat_score")
        )

        heat_threshold = self.find_threshold(historical_data, percentile_threshold)
        percentile = percentileofscore(historical_data["weighted_heat_score"], weighted_score)

        return (
            weighted_score > heat_threshold,
            weighted_score,
            heat_threshold,
            percentile,
        )

    def filter_data(self, nearest_stations: pd.DataFrame) -> pd.DataFrame:
        """
        Filters historical data based on the nearest weather stations.
        Parameters:
            df (pd.DataFrame): DataFrame containing historical weather data.
            nearest_stations (pd.DataFrame): DataFrame containing the nearest weather stations.
        Returns:
            pd.DataFrame: Filtered DataFrame containing historical data for the nearest stations.
        """
        return self.DATA[self.DATA["stationId"].isin(nearest_stations["stationId"])]

    def set_location(self, postal_code: str):
        """
        Sets the user's location based on a postal code.
        Parameters:
            postal_code (str): The postal code of the user's location.
        """
        lat_lon = self.postal_code_to_latlong(postal_code)
        if lat_lon:
            self.LAT, self.LON = lat_lon
        else:
            raise ValueError(f"Could not find coordinates for postal code: {postal_code}")