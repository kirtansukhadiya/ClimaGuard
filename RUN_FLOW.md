# ClimaGuard Execution Flow

This document explains the correct order to run the ClimaGuard system files.

## 📋 Prerequisites (One-Time Setup)

Before running anything, complete these steps:

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Setup database:**
   ```bash
   mysql -u your_user -p < sql/schema.sql
   ```

3. **Configure environment:**
   ```bash
   cp env.example .env
   # Edit .env with your actual credentials
   ```

---

## 🔄 Daily Pipeline Flow

### **Step 1: Ingest Raw Data** → `src/ingest.py`

**Purpose:** Fetch current weather and air quality data from OpenWeatherMap API and store in `weather_raw` table.

**Command:**
```bash
python src/ingest.py Toronto
```

**What it does:**
- Fetches current weather for the specified city
- Fetches air quality data
- Stores everything in `weather_raw` table

**Run this:**
- Once per day (or multiple times for different cities)
- Before running `features.py`

**Output:** Data in `weather_raw` table

---

### **Step 2: Process Features** → `src/features.py`

**Purpose:** Aggregate raw data into daily features and compute risk levels.

**Command:**
```bash
python src/features.py
```

**What it does:**
- Reads from `weather_raw` table
- Groups by city and date
- Computes daily aggregates (min/avg temp, wind speed, humidity, AQI)
- Calculates wind chill
- Computes risk levels (Low/Moderate/High)
- Stores in `weather_daily` table

**Run this:**
- After `ingest.py` (can run multiple times, handles duplicates)
- Once per day after data ingestion

**Output:** Data in `weather_daily` table

---

### **Step 3: Train Models** → `src/train.py`

**Purpose:** Train machine learning models on historical daily data.

**Command:**
```bash
python src/train.py
```

**What it does:**
- Reads from `weather_daily` table
- Trains Logistic Regression model
- Trains XGBoost model
- Saves models to `models/` directory:
  - `logistic_regression.joblib`
  - `scaler.joblib`
  - `xgboost.joblib`
  - `risk_mapping.joblib`
  - `feature_names.joblib`

**Run this:**
- After you have at least 2-3 days of data in `weather_daily`
- Periodically (weekly/monthly) to retrain with new data
- Before starting the API server

**Requirements:**
- Need at least 2-3 days of data with different risk levels
- More data = better model performance

**Output:** Trained models in `models/` directory

---

### **Step 4: Start API Server** → `src/service.py`

**Purpose:** Start FastAPI server to serve predictions via REST API.

**Command:**
```bash
uvicorn src.service:app --reload --host 0.0.0.0 --port 8000
```

**Or:**
```bash
python src/service.py
```

**What it does:**
- Loads trained models from `models/` directory
- Starts FastAPI server on port 8000
- Provides `/risk` and `/history` endpoints
- Can make predictions in real-time

**Run this:**
- After models are trained
- Keep running while you want to use the API
- Can run continuously in production

**Endpoints:**
- `http://localhost:8000/risk?city=Toronto` - Get risk prediction
- `http://localhost:8000/history?city=Toronto&days=30` - Get history
- `http://localhost:8000/health` - Health check

---

### **Step 5: Open Dashboard** → `web/index.html`

**Purpose:** Visual dashboard to view predictions and history.

**How to use:**
1. Open `web/index.html` in a web browser
2. Or serve it:
   ```bash
   cd web
   python -m http.server 8080
   ```
3. Open `http://localhost:8080` in browser

**What it does:**
- Calls FastAPI endpoints
- Displays risk predictions
- Shows historical charts and data

**Run this:**
- After API server is running
- Anytime you want to view the dashboard

---

## 📊 Complete Flow Diagram

```
┌─────────────────┐
│   Setup (Once)  │
│ 1. Install deps  │
│ 2. Setup DB     │
│ 3. Create .env   │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Daily Pipeline │
│                 │
│  Step 1:        │
│  ingest.py      │───► weather_raw table
│  (fetch data)   │
│                 │
│  Step 2:        │
│  features.py    │───► weather_daily table
│  (aggregate)    │
│                 │
│  Step 3:        │
│  train.py       │───► models/*.joblib
│  (train models) │
│                 │
│  Step 4:        │
│  service.py     │───► FastAPI server
│  (start API)    │
│                 │
│  Step 5:        │
│  index.html     │───► Dashboard UI
│  (view results) │
└─────────────────┘
```

---

## 🚀 Quick Start (First Time)

**Complete setup and run once:**

```bash
# 1. Setup
pip install -r requirements.txt
cp env.example .env
# Edit .env with your credentials
mysql -u user -p < sql/schema.sql

# 2. Collect initial data (run multiple times for different cities/days)
python src/ingest.py Toronto
python src/ingest.py "New York"
python src/ingest.py London

# 3. Process features
python src/features.py

# 4. Train models (need at least 2-3 days of data)
python src/train.py

# 5. Start API
uvicorn src.service:app --reload

# 6. Open dashboard (in another terminal)
cd web
python -m http.server 8080
# Open http://localhost:8080 in browser
```

---

## 🔁 Daily Workflow (After Initial Setup)

**For daily operations, run in this order:**

```bash
# Morning: Collect today's data
python src/ingest.py Toronto

# Process features
python src/features.py

# (Optional) Retrain models weekly/monthly
python src/train.py

# Start/restart API (if not already running)
uvicorn src.service:app --reload
```

---

## 📝 File Dependencies

```
ingest.py
  └─► Requires: .env file, MySQL database, OpenWeatherMap API key
  └─► Creates: weather_raw table data

features.py
  └─► Requires: weather_raw table data
  └─► Creates: weather_daily table data

train.py
  └─► Requires: weather_daily table data (at least 2-3 days)
  └─► Creates: models/*.joblib files

service.py
  └─► Requires: models/*.joblib files, weather_daily table
  └─► Creates: predictions table data, API endpoints

index.html
  └─► Requires: service.py running (API server)
  └─► Creates: Dashboard UI
```

---

## ⚠️ Common Issues

### "No weather data found"
- **Solution:** Run `ingest.py` first

### "Models not loaded"
- **Solution:** Run `train.py` first (need data in weather_daily)

### "No training data found"
- **Solution:** Run `ingest.py` and `features.py` first, collect 2-3 days of data

### "Database connection error"
- **Solution:** Check `.env` file has correct database credentials

---

## 🎯 Summary

**Minimum flow to get predictions:**
1. `ingest.py` → Collect data
2. `features.py` → Process features  
3. `train.py` → Train models (after 2-3 days of data)
4. `service.py` → Start API
5. `index.html` → View dashboard

**Daily flow:**
1. `ingest.py` → Collect today's data
2. `features.py` → Update daily features
3. (Optional) `train.py` → Retrain periodically
4. `service.py` → Keep running

