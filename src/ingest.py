import requests
import os
from dotenv import dotenv_values

dotenv_values(".env")
currentWeatherApiKey = os.getenv("CURRENT_WEATHER_API_URL")
airPollutionApiKey = os.getenv("AIR_POLLUTION_API_URL")

rw = requests.get(currentWeatherApiKey)
ra = requests.get(airPollutionApiKey)
print(rw.json())
print(ra.text)