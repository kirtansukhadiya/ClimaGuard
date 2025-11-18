# ClimaGuard Setup & Run Guide

## Prerequisites

1. **Python 3.8+** installed
2. **MySQL** database server running
3. **OpenWeatherMap API Key** (get from https://openweathermap.org/api)

## Setup Steps

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure Environment

**IMPORTANT: Never commit your `.env` file to version control!**

Create a `.env` file in the project root by copying the example:

```bash
cp env.example .env
```

Then edit `.env` and replace the placeholder values with your actual credentials:

```bash
# OpenWeatherMap API Configuration
OPENWEATHER_API_KEY=your_actual_api_key_here

# MySQL Database Configuration
DB_USER=your_actual_db_user
DB_PASSWORD=your_actual_db_password
DB_HOST=localhost
DB_NAME=climaguard
```

**Security Note:**
- The `.env` file is already in `.gitignore` and will not be committed
- Never share your `.env` file or commit it to version control
- Keep your API keys and database passwords secure

### 3. Setup Database

1. Create the MySQL database:
```sql
CREATE DATABASE climaguard;
```

2. Run the schema script:
```bash
mysql -u your_db_user -p climaguard < sql/schema.sql
```

Or execute `sql/schema.sql` in MySQL Workbench.

### 4. Run the Pipeline

#### Step 1: Ingest Data
Fetch weather and air quality data for a city:

```bash
python src/ingest.py Toronto
```

Or for multiple cities:
```bash
python src/ingest.py "New York"
python src/ingest.py "London"
```

**Note:** Run this multiple times or schedule it to collect historical data.

#### Step 2: Process Features
Aggregate raw data into daily features:

```bash
python src/features.py
```

This will:
- Read from `weather_raw` table
- Compute daily aggregates (min/avg temp, wind speed, humidity, AQI)
- Calculate wind chill
- Compute risk levels
- Store in `weather_daily` table

#### Step 3: Train Models
Train both Logistic Regression and XGBoost models:

```bash
python src/train.py
```

This will:
- Load data from `weather_daily`
- Train both models
- Save models to `models/` directory:
  - `logistic_regression.joblib`
  - `scaler.joblib`
  - `xgboost.joblib`
  - `risk_mapping.joblib`
  - `feature_names.joblib`

**Note:** You need at least 2-3 days of data with different risk levels for training.

#### Step 4: Start FastAPI Server

```bash
uvicorn src.service:app --reload --host 0.0.0.0 --port 8000
```

Or:
```bash
python src/service.py
```

The API will be available at: `http://localhost:8000`

#### Step 5: Open Dashboard

Open `web/index.html` in your browser, or serve it:

```bash
# Using Python's built-in server
cd web
python -m http.server 8080
```

Then open: `http://localhost:8080`

## API Endpoints

### GET /risk?city=Toronto
Get risk prediction for a city.

**Response:**
```json
{
  "city": "Toronto",
  "date": "2025-01-15",
  "risk": "Moderate",
  "confidence": 0.85,
  "top_reasons": ["min_temp_c", "mean_aqi", "wind_chill"]
}
```

### GET /history?city=Toronto&days=30
Get historical weather data and predictions.

**Response:**
```json
{
  "city": "Toronto",
  "entries": [
    {
      "date": "2025-01-15",
      "min_temp_c": -5.0,
      "avg_temp_c": 2.0,
      "wind_speed": 5.0,
      "humidity": 75.0,
      "wind_chill": -8.0,
      "mean_aqi": 3.0,
      "risk_level": "Moderate",
      "predicted_risk": "Moderate",
      "confidence": 0.85
    }
  ]
}
```

### GET /health
Health check endpoint.

## Daily Pipeline

For production, set up a daily cron job or scheduled task:

```bash
# Daily at 6 AM
0 6 * * * cd /path/to/ClimaGuard && python src/ingest.py Toronto
0 7 * * * cd /path/to/ClimaGuard && python src/features.py
0 8 * * * cd /path/to/ClimaGuard && python src/train.py
```

## Execution Flow

**See `RUN_FLOW.md` for detailed step-by-step execution order and dependencies.**

Quick reference:
1. **First time:** `ingest.py` → `features.py` → `train.py` → `service.py` → `index.html`
2. **Daily:** `ingest.py` → `features.py` → (optional) `train.py`
3. **Always running:** `service.py` (API server)

## Troubleshooting

### "No weather data found"
- Run `ingest.py` first to fetch data
- Check your OpenWeatherMap API key is valid
- Verify database connection in `.env`

### "Models not loaded"
- Run `train.py` to train models
- Ensure `models/` directory contains `.joblib` files
- Check that you have enough training data (at least 2-3 days)

### "Database connection error"
- Verify MySQL is running
- Check `.env` file has correct credentials
- Ensure database `climaguard` exists
- Run `sql/schema.sql` to create tables

### SHAP explanation fails
- The API will fall back to direct prediction without SHAP
- This is normal if SHAP library has issues
- Predictions will still work, just without top_reasons

## Project Structure

```
ClimaGuard/
├── src/
│   ├── ingest.py      # Fetch & store raw weather data
│   ├── features.py    # Aggregate daily features
│   ├── train.py       # Train ML models
│   ├── explain.py     # SHAP explanations
│   └── service.py     # FastAPI server
├── web/
│   └── index.html     # Dashboard
├── models/            # Trained models (created after training)
├── sql/
│   └── schema.sql    # Database schema
├── .env              # Environment variables (create this)
└── requirements.txt  # Python dependencies
```

## Next Steps

1. Collect more data by running `ingest.py` multiple times
2. Retrain models periodically with `train.py`
3. Customize risk thresholds in `features.py`
4. Add more cities to monitor
5. Set up automated daily pipeline

