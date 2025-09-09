import requests
from dotenv import dotenv_values
from mysql.connector import (connection)
from datetime import datetime, timezone

# Load environment variables
env = dotenv_values(".env")
currentWeatherApiKey = env.get("CURRENT_WEATHER_API_URL")
airPollutionApiKey = env.get("AIR_POLLUTION_API_URL")
historyApiKey = env.get("HISTORY_API_URL")
db_user = env.get("DB_USER")
db_password = env.get("DB_PASSWORD")
db_host = env.get("DB_HOST")
db_name = env.get("DB_NAME")

rw = requests.get(currentWeatherApiKey) # response for current weather from open weather api
ra = requests.get(airPollutionApiKey) # response for air quality from open weather api
rh = requests.get(historyApiKey) # response for historical weather from open weather api

rw_data = rw.json()
ra_data = ra.json()
rh_data = rh.json()
#print(rh_data)

# Functions to extract relevant data
def get_current_weather():
    weather = {
        "temp_c": rw_data["main"]["temp"],
        "min_temp_c": rw_data["main"]["temp_min"],
        "max_temp_c": rw_data["main"]["temp_max"],
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
        "pm25": ra_data["list"][0]["components"]["pm2_5"],
        "pm10": ra_data["list"][0]["components"]["pm10"],
        "nh3": ra_data["list"][0]["components"]["nh3"]
    }
    return air_quality

def get_historical_weather():
    weather_dicts = []
    for entry in rh_data["list"]:
        row = {
            "temp_c": entry["main"]["temp"],
            "humidity": entry["main"]["humidity"],
            "pressure": entry["main"]["pressure"],
            "weather_description": entry["weather"][0]["description"],
            "wind_speed": entry["wind"]["speed"],
            "wind_direction": entry["wind"]["deg"],
            "cloudiness": entry["clouds"]["all"],
            "ts": datetime.fromtimestamp(entry["dt"], tz=timezone.utc).strftime('%Y-%m-%d %H:%M:%S')
        }
        weather_dicts.append(row)
    return weather_dicts

all_data = {**get_current_weather(), **get_air_quality()}
historical_data = get_historical_weather()

#SQL connection and insertion
try :
    config = {
    'user': db_user,
    'password': db_password,
    'host': db_host,
    'database': db_name
}

    db = connection.MySQLConnection(**config)
    print("Connected to %s database"% db.database)
    cursor = db.cursor()
    columns = ', '.join(all_data.keys())                 
    placeholders = ', '.join(['%s'] * len(all_data))         
    values = tuple(all_data.values())
    query = f"INSERT INTO weather_raw ({columns}) VALUES ({placeholders})"
    cursor.execute(query, values)

    hist_columns =', '.join(historical_data[0].keys())
    hist_placeholders = ', '.join(['%s'] * len(historical_data[0]))
    hist_values = [tuple(d.values()) for d in historical_data]
    hist_query = f"INSERT INTO weather_raw ({hist_columns}) VALUES ({hist_placeholders})"
    cursor.executemany(hist_query, hist_values)
    db.commit()
    print("Data inserted successfully")
    cursor.close()
    db.close()
except Exception as e:
    print(f"Error: {e}")