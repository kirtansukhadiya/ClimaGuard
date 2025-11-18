import requests
from dotenv import dotenv_values
from mysql.connector import connection
from datetime import datetime, timezone
import sys
import os

env = dotenv_values(".env")

if not env:
    raise ValueError(".env file not found! Please create a .env file based on env.example.")

OPENWEATHER_API_KEY = env.get("OPENWEATHER_API_KEY")
db_user = env.get("DB_USER")
db_password = env.get("DB_PASSWORD")
db_host = env.get("DB_HOST")
db_name = env.get("DB_NAME")

if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "your_openweather_api_key_here":
    import warnings
    warnings.warn("OPENWEATHER_API_KEY not set in .env file.")


def get_current_weather(city="Toronto", api_key=None):
    if api_key is None:
        api_key = OPENWEATHER_API_KEY
    
    if not api_key:
        raise ValueError("OpenWeatherMap API key is required. Set OPENWEATHER_API_KEY in .env")
    
    url = f"http://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": api_key,
        "units": "metric"
    }
    
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        weather = {
            "city": data["name"],
            "ts": datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            "temp_c": data["main"]["temp"],
            "min_temp_c": data["main"]["temp_min"],
            "max_temp_c": data["main"]["temp_max"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "weather_description": data["weather"][0]["description"],
            "wind_speed": data.get("wind", {}).get("speed", 0),
            "wind_direction": data.get("wind", {}).get("deg", 0),
            "cloudiness": data.get("clouds", {}).get("all", 0)
        }
        return weather
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch weather data: {e}")


def get_air_quality(city="Toronto", api_key=None):
    if api_key is None:
        api_key = OPENWEATHER_API_KEY
    
    if not api_key:
        raise ValueError("OpenWeatherMap API key is required. Set OPENWEATHER_API_KEY in .env")
    
    geo_url = f"http://api.openweathermap.org/geo/1.0/direct"
    geo_params = {
        "q": city,
        "limit": 1,
        "appid": api_key
    }
    
    try:
        geo_response = requests.get(geo_url, params=geo_params, timeout=10)
        geo_response.raise_for_status()
        geo_data = geo_response.json()
        
        if not geo_data:
            raise ValueError(f"City '{city}' not found")
        
        lat = geo_data[0]["lat"]
        lon = geo_data[0]["lon"]
        
        aq_url = f"http://api.openweathermap.org/data/2.5/air_pollution"
        aq_params = {
            "lat": lat,
            "lon": lon,
            "appid": api_key
        }
        
        aq_response = requests.get(aq_url, params=aq_params, timeout=10)
        aq_response.raise_for_status()
        aq_data = aq_response.json()
        
        components = aq_data["list"][0]["components"]
        air_quality = {
            "aqi": aq_data["list"][0]["main"]["aqi"],
            "co": components.get("co", 0),
            "no_": components.get("no", 0),
            "no2": components.get("no2", 0),
            "o3": components.get("o3", 0),
            "so2": components.get("so2", 0),
            "pm25": components.get("pm2_5", 0),
            "pm10": components.get("pm10", 0),
            "nh3": components.get("nh3", 0)
        }
        return air_quality
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to fetch air quality data: {e}")


def store_weather_data(weather_data, air_quality_data, db_user=None, db_password=None, 
                      db_host=None, db_name=None):
    if db_user is None:
        db_user = env.get("DB_USER")
    if db_password is None:
        db_password = env.get("DB_PASSWORD")
    if db_host is None:
        db_host = env.get("DB_HOST")
    if db_name is None:
        db_name = env.get("DB_NAME")
    
    if not all([db_user, db_password, db_host, db_name]):
        raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
    
    all_data = {**weather_data, **air_quality_data}
    
    try:
        config = {
            'user': db_user,
            'password': db_password,
            'host': db_host,
            'database': db_name
        }
        
        db = connection.MySQLConnection(**config)
        cursor = db.cursor()
        
        columns = ', '.join(all_data.keys())
        placeholders = ', '.join(['%s'] * len(all_data))
        values = tuple(all_data.values())
        
        query = f"INSERT INTO weather_raw ({columns}) VALUES ({placeholders})"
        cursor.execute(query, values)
        
        db.commit()
        cursor.close()
        db.close()
        
        return True
    except Exception as e:
        print(f"Error storing data: {e}")
        return False


def ingest_data(city="Toronto"):
    try:
        print(f"Fetching weather data for {city}...")
        weather_data = get_current_weather(city)
        
        print(f"Fetching air quality data for {city}...")
        air_quality_data = get_air_quality(city)
        
        print(f"Storing data in database...")
        success = store_weather_data(weather_data, air_quality_data)
        
        if success:
            print(f"Data successfully ingested for {city}")
            return True
        else:
            print(f"Failed to store data for {city}")
            return False
    except Exception as e:
        print(f"Error ingesting data: {e}")
        return False


if __name__ == "__main__":
    city = sys.argv[1] if len(sys.argv) > 1 else "Toronto"
    ingest_data(city)