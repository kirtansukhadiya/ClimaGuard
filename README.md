# ClimaGuard
# 🌍 Heat & Air Quality Early-Warning (H-AQ Alert)

A data science project that predicts **next-day heat and air quality risk levels** (Low / Moderate / High) for a given city.  
The system ingests weather + air pollution data, stores it in a **MySQL database**, trains ML models (Logistic Regression / XGBoost), and exposes predictions through a **FastAPI REST API** with a simple web dashboard.

---

## 🚨 Why this project?
Climate change is driving **extreme heat waves** and **poor air quality**, which threaten public health.  
This project provides an early-warning tool to help people and communities prepare for unsafe conditions.

---

## ✨ Features
- 🔗 **Automated Data Ingestion** from [OpenWeatherMap API](https://openweathermap.org/api)  
- 🗄️ **SQL Database** (MySQL) for structured storage & analytics  
- 📊 **Daily Feature Engineering** (rolling averages, 3-day trends, heat index)  
- 🤖 **Machine Learning Models**  
  - Logistic Regression (baseline, interpretable)  
  - XGBoost (boosted accuracy)  
- 🧾 **Explainability** using SHAP to show *why* a day is “High Risk”  
- ⚡ **REST API** (FastAPI) with `/risk` and `/history` endpoints  
- 💻 **Lightweight Dashboard** (HTML/JS) showing recent trends + tomorrow’s risk  

---

## 🛠️ Tech Stack
- **Languages:** Python, SQL  
- **Database:** MySQL  
- **Libraries:**
  - Data: `pandas`, `numpy`, `sqlalchemy`, `mysql-connector-python`
  - ML: `scikit-learn`, `xgboost`, `shap`
  - API: `fastapi`, `uvicorn`, `requests`, `python-dotenv`
  - Viz: `matplotlib`, `seaborn`
- **Frontend:** HTML, CSS, JavaScript

---

## 📂 Project Structure

```bash
h-aq-alert/
│
├── sql/
│   └── schema.sql            # MySQL database schema (tables for raw + daily data + predictions)
│
├── src/
│   ├── ingest.py             # Fetch weather & air quality data from API → store in MySQL
│   ├── features.py           # Clean & aggregate raw data → daily features for ML
│   ├── train.py              # Train Logistic Regression / XGBoost model & save
│   ├── explain.py            # Generate SHAP explanations for predictions
│   └── service.py            # FastAPI backend exposing /risk and /history endpoints
│
├── web/
│   └── index.html            # Simple dashboard (calls FastAPI endpoints to show results)
│
├── tests/
│   └── test_service.py       # Unit tests for the FastAPI backend
│
├── models/                   # Folder to store trained ML models (.joblib files)
│
├── scripts/
│   └── eda.py                # Exploratory Data Analysis (EDA) & visualization in Python
│
├── .env.example              # Example file for API keys & DB credentials
├── requirements.txt          # List of Python dependencies (pinned versions)
└── README.md                 # Project documentation
```
---

## Example Output

```bash
GET /risk?city=Toronto
{
  "city": "Toronto",
  "date": "2025-09-05",
  "risk": "High",
  "confidence": 0.82,
  "top_reasons": ["max_temp_c", "mean_aqi", "temp_trend_3d"]
}
```


