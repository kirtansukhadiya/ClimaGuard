import requests
import os
from dotenv import dotenv_values
from mysql.connector import (connection)
from datetime import datetime

# Load environment variables
dotenv_values(".env")
currentWeatherApiKey = os.getenv("CURRENT_WEATHER_API_URL")
airPollutionApiKey = os.getenv("AIR_POLLUTION_API_URL")
historyApiKey = os.getenv("HISTORY_API_URL")
db_user = os.getenv("DB_USER")
db_password = os.getenv("DB_PASSWORD")
db_host = os.getenv("DB_HOST")
db_name = os.getenv("DB_NAME")

rw = requests.get(currentWeatherApiKey) # response for current weather from open weather api
ra = requests.get(airPollutionApiKey) # response for air quality from open weather api
rh = requests.get(historyApiKey) # response for historical weather from open weather api

rw_data = rw.json()
ra_data = ra.json()
rh_data = rh.json()

# Functions to extract relevant data
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
        "no_": ra_data["list"][0]["components"]["no"],
        "no2": ra_data["list"][0]["components"]["no2"],
        "o3": ra_data["list"][0]["components"]["o3"],
        "so2": ra_data["list"][0]["components"]["so2"],
        "pm2_5": ra_data["list"][0]["components"]["pm2_5"],
        "pm10": ra_data["list"][0]["components"]["pm10"],
        "nh3": ra_data["list"][0]["components"]["nh3"]
    }
    return air_quality

def get_historical_weather():
    historical_weather = {
        "temperature": rh_data["list"][0]["main"]["temp"],
        "humidity": rh_data["list"][0]["main"]["humidity"],
        "pressure": rh_data["list"][0]["main"]["pressure"],
        "weather_description": rh_data["list"][0]["weather"][0]["description"],
        "wind_speed": rh_data["list"][0]["wind"]["speed"],
        "wind_direction": rh_data["list"][0]["wind"]["deg"],
        "cloudiness": rh_data["list"][0]["clouds"]["all"],
         
    }
    return historical_weather

#SQL connection and insertion
try :
    config = {
    'user': db_user,
    'password': db_password,
    'host': db_host,
    'database': db_name
}

    db = connection.MySQLConnection(**config)
    cursor = db.cursor()
    cursor.execute = ("INSERT INTO weather_raw "
            "(city, ts, temp_c, min_temp_c, max_temp_c, wind_speed, humidity, aqi, pm25, pm10, weather_description, wind_direction, cloudiness, co, no_, no2, o3, so2, nh3)"
            "VALUES (:city, :ts, :temp_c, :min_temp_c, :max_temp_c, :wind_speed, :humidity, :aqi, :pm25, :pm10, :weather_description, :wind_direction, :cludiness, :co, :no_, :no2, :o3, :so2, :nh3)", get_air_quality(), get_current_weather(), get_historical_weather())
    db.commit()
    print("Data inserted successfully")
except Exception as e:
    print(f"Error: {e}")