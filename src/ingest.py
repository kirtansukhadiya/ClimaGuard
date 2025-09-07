import requests
import os
from dotenv import dotenv_values

dotenv_values(".env")
currentWeatherApiKey = os.getenv("CURRENT_WEATHER_API_URL")
airPollutionApiKey = os.getenv("AIR_POLLUTION_API_URL")

rw = requests.get(currentWeatherApiKey) # response for current weather from open weather api
ra = requests.get(airPollutionApiKey) # response for air quality from open weather api


rw_data = rw.json()
ra_data = ra.json()

def get_current_weather():
    weather = {
        "temperature": rw_data["main"]["temp"],
        "humidity": rw_data["main"]["humidity"],
        "pressure": rw_data["main"]["pressure"],
        "weather_description": rw_data["weather"][0]["description"],
        "wind_speed": rw_data["wind"]["speed"],
        "wind_direction": rw_data["wind"]["deg"],
        "cloudiness": rw_data["clouds"]["all"],
        "city": rw_data["name"]
    }
    return weather

def get_air_quality():
    air_quality = {
        "aqi": ra_data["list"][0]["main"]["aqi"],
        "co": ra_data["list"][0]["components"]["co"],
        "no": ra_data["list"][0]["components"]["no"],
        "no2": ra_data["list"][0]["components"]["no2"],
        "o3": ra_data["list"][0]["components"]["o3"],
        "so2": ra_data["list"][0]["components"]["so2"],
        "pm2_5": ra_data["list"][0]["components"]["pm2_5"],
        "pm10": ra_data["list"][0]["components"]["pm10"],
        "nh3": ra_data["list"][0]["components"]["nh3"]
    }
    return air_quality