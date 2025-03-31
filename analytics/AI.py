from google import genai
import json

class AI:
    PROMPT = """You are an assistant that provides weather-based home comfort and energy-saving suggestions. Given the following data in json format:
    House orientation: The direction the house is facing.
    is_hotspot: Whether the location is a heat hotspot based on the heat score and threshold.
    Heat threshold: The heat score value above which the weather is considered hot.
    Weighted heat score: A weighted value based on normalised air temperature, humidity, and wind speed from the 3 nearest weather stations.
    Heat score percentile: The percentile ranking of the current heat score compared to past data.
    Weather station measurements: Weather data from the 3 nearest stations.

    Data:
    {data}

    Your task:
        1. Summarize the current weather conditions in natural language by incorporating house orientation, air temperature, wind direction, and humidity.
        2. Analyze the computed heat score in relation to the threshold and historical percentiles.
        3. Generate a suggestion for the user based on the following criteria:
            If the weather is hot, suggest ways to feel cooler at home (e.g., ventilation strategies, optimal curtain use, using fans effectively).
            If the weather is cool, suggest ways to save energy (e.g., reducing unnecessary AC usage, optimizing natural light).
            If the wind direction is favorable for ventilation, suggest ways to maximize airflow.
        4. Formulate a response composing of 2 parts:
            1. A summary of the current weather conditions.
            2. A suggestion for improving comfort or saving energy based on the weather conditions. Ensure the suggestion is relevant to the specific weather conditions and keep it to 3 sentences. Be specific in mentioning specific rooms or areas of the house.
        Do not include any other information or the logic used to determine hotspots. The response should be concise and actionable.

    Output format example:
    Summary: The air temperature is around []°C and the humidity is around []. Your house is facing [] and the current wind direction and speed is []. Overall, the weather is [], and is hotter than []% of historical data.
    Suggestions: Even though it's not a hotspot, consider opening windows on the south and east sides of your house to take advantage of the breezes. Drawing bedroom curtains during the day may help you feel cool while conserving energy.
    """

    def __init__(self, config: dict):
        self.CLIENT = genai.Client(api_key=config["GEMINI_KEY"])
        self.CONFIG = config

    def generate_suggestions(self, data_dict: dict) -> str:
        # print(data_dict)
        prompt = self.PROMPT.format(data=json.dumps(data_dict, indent=4))
        response = self.CLIENT.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
        )

        return response.text


