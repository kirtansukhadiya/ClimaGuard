from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date, timedelta
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
import joblib
import os
import numpy as np

try:
    from src.explain import explain_prediction
except ImportError:
    from explain import explain_prediction

env = dotenv_values(".env")

if not env:
    import warnings
    warnings.warn(".env file not found! Please create a .env file based on env.example.")

db_user = env.get("DB_USER")
db_password = env.get("DB_PASSWORD")
db_host = env.get("DB_HOST")
db_name = env.get("DB_NAME")

app = FastAPI(title="ClimaGuard API", description="Cold & Air Quality Early Warning System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = None
models = {}


def get_db_engine():
    global engine
    if engine is None:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
    return engine


def load_models():
    global models
    model_dir = "models"
    
    if not os.path.exists(model_dir):
        raise FileNotFoundError(f"Models directory not found: {model_dir}. Run train.py first.")
    
    # Try to load XGBoost (preferred)
    xgboost_path = os.path.join(model_dir, "xgboost.joblib")
    if os.path.exists(xgboost_path):
        models['xgboost'] = joblib.load(xgboost_path)
        models['model_type'] = 'xgboost'
        print("Loaded XGBoost model")
    else:
        # Fall back to Logistic Regression
        logistic_path = os.path.join(model_dir, "logistic_regression.joblib")
        if os.path.exists(logistic_path):
            models['logistic'] = joblib.load(logistic_path)
            scaler_path = os.path.join(model_dir, "scaler.joblib")
            if os.path.exists(scaler_path):
                models['scaler'] = joblib.load(scaler_path)
            models['model_type'] = 'logistic'
            print("Loaded Logistic Regression model")
        else:
            raise FileNotFoundError("No trained models found. Run train.py first.")
    
    # Load risk mapping and feature names
    risk_mapping_path = os.path.join(model_dir, "risk_mapping.joblib")
    if os.path.exists(risk_mapping_path):
        models['risk_mapping'] = joblib.load(risk_mapping_path)
    
    feature_names_path = os.path.join(model_dir, "feature_names.joblib")
    if os.path.exists(feature_names_path):
        models['feature_names'] = joblib.load(feature_names_path)
    else:
        models['feature_names'] = ['min_temp_c', 'avg_temp_c', 'wind_speed', 'humidity', 'wind_chill', 'mean_aqi']


@app.on_event("startup")
async def startup_event():
    try:
        load_models()
        print("Models loaded successfully")
    except Exception as e:
        print(f"Warning: Could not load models: {e}")
        print("API will still start, but /risk endpoint may not work until models are trained.")


class RiskResponse(BaseModel):
    city: str
    date: str
    risk: str
    confidence: float
    top_reasons: List[str]


class HistoryEntry(BaseModel):
    date: str
    min_temp_c: float
    avg_temp_c: float
    wind_speed: float
    humidity: float
    wind_chill: float
    mean_aqi: float
    risk_level: Optional[str] = None
    predicted_risk: Optional[str] = None
    confidence: Optional[float] = None


class HistoryResponse(BaseModel):
    city: str
    entries: List[HistoryEntry]


@app.get("/")
async def root():
    return {
        "message": "ClimaGuard API - Cold & Air Quality Early Warning System",
        "endpoints": {
            "/risk": "Get risk prediction for a city",
            "/history": "Get historical weather and predictions for a city",
            "/health": "Health check endpoint"
        }
    }


@app.get("/health")
async def health():
    return {"status": "healthy", "models_loaded": "model_type" in models}


@app.get("/risk", response_model=RiskResponse)
async def get_risk(
    city: str = Query(..., description="City name"),
    model_type: Optional[str] = Query("xgboost", description="Model type: xgboost or logistic")
):
    try:
        if 'model_type' not in models:
            raise HTTPException(status_code=503, detail="Models not loaded. Run train.py first.")
        
        if model_type not in models and model_type != models.get('model_type'):
            model_type = models.get('model_type', 'xgboost')
        
        engine = get_db_engine()
        
        query = text("""
            SELECT * FROM weather_daily 
            WHERE city = :city 
            ORDER BY date DESC, created_at DESC 
            LIMIT 1
        """)
        df = pd.read_sql(query, engine, params={'city': city})
        
        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No weather data found for city: {city}. Run ingest.py and features.py first."
            )
        
        row = df.iloc[0]
        feature_names = models.get('feature_names', ['min_temp_c', 'avg_temp_c', 'wind_speed', 'humidity', 'wind_chill', 'mean_aqi'])
        features = {name: float(row[name]) for name in feature_names if name in row}
        
        prediction_date = date.today()
        
        try:
            explanation = explain_prediction(
                features,
                model_type=model_type,
                model_dir="models",
                top_n=3
            )
            
            predicted_risk = explanation['prediction']
            confidence = explanation['confidence']
            top_reasons = explanation['top_reasons']
        except Exception as e:
            print(f"Warning: SHAP explanation failed: {e}. Using direct prediction.")
            
            model = models.get(model_type) or models.get('xgboost') or models.get('logistic')
            if not model:
                raise HTTPException(status_code=503, detail="No model available")
            
            feature_array = np.array([[features.get(f, 0) for f in feature_names]])
            
            if model_type == 'logistic' and 'scaler' in models:
                feature_array = models['scaler'].transform(feature_array)
            
            prediction_proba = model.predict_proba(feature_array)[0]
            prediction_idx = np.argmax(prediction_proba)
            confidence = float(prediction_proba[prediction_idx])
            
            risk_mapping = models.get('risk_mapping', {'Low': 0, 'Moderate': 1, 'High': 2})
            reverse_mapping = {v: k for k, v in risk_mapping.items()}
            predicted_risk = reverse_mapping.get(prediction_idx, "Unknown")
            top_reasons = feature_names[:3]
        
        try:
            with engine.connect() as conn:
                insert_query = text("""
                    INSERT INTO predictions (city, date, predicted_risk, confidence)
                    VALUES (:city, :date, :predicted_risk, :confidence)
                    ON DUPLICATE KEY UPDATE
                        predicted_risk = VALUES(predicted_risk),
                        confidence = VALUES(confidence),
                        created_at = CURRENT_TIMESTAMP
                """)
                conn.execute(insert_query, {
                    'city': city,
                    'date': prediction_date,
                    'predicted_risk': predicted_risk,
                    'confidence': confidence
                })
                conn.commit()
        except Exception as e:
            print(f"Warning: Could not store prediction in database: {e}")
        
        return RiskResponse(
            city=city,
            date=prediction_date.isoformat(),
            risk=predicted_risk,
            confidence=confidence,
            top_reasons=top_reasons
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting risk prediction: {str(e)}")


@app.get("/history", response_model=HistoryResponse)
async def get_history(
    city: str = Query(..., description="City name"),
    days: int = Query(30, ge=1, le=365, description="Number of days to retrieve (1-365)")
):
    try:
        engine = get_db_engine()
        
        end_date = date.today()
        start_date = end_date - timedelta(days=days)
        
        weather_query = text("""
            SELECT * FROM weather_daily 
            WHERE city = :city AND date >= :start_date AND date <= :end_date
            ORDER BY date DESC
        """)
        weather_df = pd.read_sql(weather_query, engine, params={
            'city': city,
            'start_date': start_date,
            'end_date': end_date
        })
        
        pred_query = text("""
            SELECT * FROM predictions 
            WHERE city = :city AND date >= :start_date AND date <= :end_date
            ORDER BY date DESC
        """)
        pred_df = pd.read_sql(pred_query, engine, params={
            'city': city,
            'start_date': start_date,
            'end_date': end_date
        })
        
        entries = []
        for _, row in weather_df.iterrows():
            row_date = row['date']
            if isinstance(row_date, str):
                row_date = datetime.strptime(row_date, '%Y-%m-%d').date()
            elif isinstance(row_date, pd.Timestamp):
                row_date = row_date.date()
            
            pred_row = pred_df[pred_df['date'] == row_date]
            predicted_risk = None
            confidence = None
            if not pred_row.empty:
                predicted_risk = pred_row.iloc[0]['predicted_risk']
                confidence = float(pred_row.iloc[0]['confidence']) if pd.notna(pred_row.iloc[0]['confidence']) else None
            
            entry = HistoryEntry(
                date=row_date.isoformat(),
                min_temp_c=float(row['min_temp_c']),
                avg_temp_c=float(row['avg_temp_c']),
                wind_speed=float(row['wind_speed']),
                humidity=float(row['humidity']),
                wind_chill=float(row['wind_chill']),
                mean_aqi=float(row['mean_aqi']),
                risk_level=row.get('risk_level'),
                predicted_risk=predicted_risk,
                confidence=confidence
            )
            entries.append(entry)
        
        return HistoryResponse(city=city, entries=entries)
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting history: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

