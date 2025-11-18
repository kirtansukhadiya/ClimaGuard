import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
from datetime import datetime, date
import numpy as np
import sys

env = dotenv_values(".env")

if not env:
    raise ValueError(".env file not found! Please create a .env file based on env.example.")

db_user = env.get("DB_USER")
db_password = env.get("DB_PASSWORD")
db_host = env.get("DB_HOST")
db_name = env.get("DB_NAME")


def compute_wind_chill(temp_c, wind_speed):
    wind_kmh = wind_speed * 3.6
    
    if temp_c > 10 or wind_kmh <= 4.8:
        return temp_c
    
    wci = 13.12 + 0.6215 * temp_c - 11.37 * (wind_kmh ** 0.16) + 0.3965 * temp_c * (wind_kmh ** 0.16)
    return wci


def compute_risk_level(min_temp_c, mean_aqi, wind_chill):
    if min_temp_c < -10 or mean_aqi >= 4 or wind_chill < -15:
        return "High"
    elif min_temp_c < 0 or mean_aqi >= 3 or wind_chill < -5:
        return "Moderate"
    else:
        return "Low"


def aggregate_daily_features(engine=None):
    if engine is None:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
    
    try:
        print("Reading raw weather data from database...")
        weather_df = pd.read_sql(text("SELECT * FROM weather_raw"), engine)
        
        if weather_df.empty:
            print("No raw weather data found in database.")
            return pd.DataFrame()
        
        weather_df['ts'] = pd.to_datetime(weather_df['ts'])
        weather_df['date'] = weather_df['ts'].dt.date
        weather_df['created_at'] = pd.to_datetime(weather_df['created_at'])
        
        weather_df = weather_df.dropna(subset=['temp_c', 'humidity', 'wind_speed', 'aqi', 'city'])
        
        if weather_df.empty:
            print("No valid weather data after cleaning.")
            return pd.DataFrame()
        
        print("Computing daily aggregates...")
        daily_features = weather_df.groupby(['city', 'date']).agg({
            'min_temp_c': 'min',
            'temp_c': 'mean',
            'wind_speed': 'mean',
            'humidity': 'mean',
            'aqi': 'mean'
        }).reset_index()
        
        daily_features.rename(columns={'temp_c': 'avg_temp_c'}, inplace=True)
        
        daily_features['wind_chill'] = daily_features.apply(
            lambda row: compute_wind_chill(row['avg_temp_c'], row['wind_speed']), axis=1
        )
        
        daily_features.rename(columns={'aqi': 'mean_aqi'}, inplace=True)
        
        daily_features['risk_level'] = daily_features.apply(
            lambda row: compute_risk_level(row['min_temp_c'], row['mean_aqi'], row['wind_chill']), axis=1
        )
        
        daily_features['date'] = pd.to_datetime(daily_features['date']).dt.date
        
        print(f"Computed daily features for {len(daily_features)} city-date combinations")
        return daily_features
        
    except Exception as e:
        print(f"Error aggregating features: {e}")
        raise


def store_daily_features(daily_features, engine=None):
    if engine is None:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
    
    if daily_features.empty:
        print("No daily features to store.")
        return 0
    
    try:
        print("Storing daily features in database...")
        
        daily_features['date'] = daily_features['date'].astype(str)
        
        with engine.connect() as conn:
            existing = pd.read_sql(
                text("SELECT city, date FROM weather_daily"),
                conn
            )
            
            if not existing.empty:
                existing['date'] = pd.to_datetime(existing['date']).dt.date.astype(str)
                existing['key'] = existing['city'] + '|' + existing['date']
                daily_features['key'] = daily_features['city'] + '|' + daily_features['date']
                
                new_features = daily_features[~daily_features['key'].isin(existing['key'])]
                daily_features = new_features.drop('key', axis=1)
            
            if daily_features.empty:
                print("All daily features already exist in database.")
                return 0
        
        daily_features.to_sql(
            'weather_daily',
            engine,
            if_exists='append',
            index=False,
            method='multi'
        )
        
        count = len(daily_features)
        print(f"Stored {count} daily feature records in database.")
        return count
        
    except Exception as e:
        print(f"Error storing daily features: {e}")
        raise


def process_features():
    try:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
        
        # Aggregate daily features
        daily_features = aggregate_daily_features(engine)
        
        if daily_features.empty:
            print("No features to process.")
            return False
        
        # Store in database
        count = store_daily_features(daily_features, engine)
        
        if count > 0:
            print(f"Successfully processed {count} daily feature records.")
            return True
        else:
            print("No new features to store.")
            return True  # Still success if nothing new to add
            
    except Exception as e:
        print(f"Error processing features: {e}")
        return False


if __name__ == "__main__":
    process_features()