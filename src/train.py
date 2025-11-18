import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import dotenv_values
import joblib
import os
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import xgboost as xgb
import numpy as np

env = dotenv_values(".env")

if not env:
    raise ValueError(".env file not found! Please create a .env file based on env.example.")

db_user = env.get("DB_USER")
db_password = env.get("DB_PASSWORD")
db_host = env.get("DB_HOST")
db_name = env.get("DB_NAME")


def load_training_data(engine=None):
    if engine is None:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
    
    try:
        print("Loading training data from database...")
        df = pd.read_sql(text("SELECT * FROM weather_daily"), engine)
        
        if df.empty:
            raise ValueError("No training data found in weather_daily table. Run features.py first.")
        
        feature_cols = ['min_temp_c', 'avg_temp_c', 'wind_speed', 'humidity', 'wind_chill', 'mean_aqi']
        
        missing_cols = [col for col in feature_cols if col not in df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
        
        df = df.dropna(subset=feature_cols + ['risk_level'])
        
        if df.empty:
            raise ValueError("No valid training data after cleaning.")
        
        X = df[feature_cols].copy()
        y = df['risk_level'].copy()
        
        unique_risk_levels = sorted(y.unique())
        print(f"Found {len(df)} training samples with risk levels: {y.value_counts().to_dict()}")
        
        if len(unique_risk_levels) < 2:
            raise ValueError(f"Need at least 2 risk level classes for training. Found: {unique_risk_levels}")
        
        full_mapping = {'Low': 0, 'Moderate': 1, 'High': 2}
        risk_mapping = {level: full_mapping[level] for level in unique_risk_levels if level in full_mapping}
        
        y_encoded = y.map(risk_mapping)
        
        reverse_mapping = {v: k for k, v in risk_mapping.items()}
        class_names = [reverse_mapping[i] for i in sorted(risk_mapping.values())]
        
        return X, y_encoded, risk_mapping, class_names
        
    except Exception as e:
        print(f"Error loading training data: {e}")
        raise


def train_logistic_regression(X, y, class_names):
    print("\nTraining Logistic Regression model...")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    model = LogisticRegression(
        solver='lbfgs',
        max_iter=1000,
        random_state=42
    )
    model.fit(X_train_scaled, y_train)
    
    y_pred = model.predict(X_test_scaled)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"Logistic Regression Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    return model, scaler


def train_xgboost(X, y, class_names):
    print("\nTraining XGBoost model...")
    
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    num_classes = len(class_names)
    
    if num_classes == 2:
        model = xgb.XGBClassifier(
            objective='binary:logistic',
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            random_state=42,
            eval_metric='logloss'
        )
    else:
        model = xgb.XGBClassifier(
            objective='multi:softprob',
            num_class=num_classes,
            max_depth=6,
            learning_rate=0.1,
            n_estimators=100,
            random_state=42,
            eval_metric='mlogloss'
        )
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    print(f"XGBoost Accuracy: {accuracy:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=class_names))
    
    return model


def save_models(logistic_model, scaler, xgboost_model, risk_mapping, model_dir="models"):
    os.makedirs(model_dir, exist_ok=True)
    
    joblib.dump(logistic_model, os.path.join(model_dir, "logistic_regression.joblib"))
    joblib.dump(scaler, os.path.join(model_dir, "scaler.joblib"))
    print(f"\nSaved Logistic Regression model to {model_dir}/logistic_regression.joblib")
    print(f"Saved scaler to {model_dir}/scaler.joblib")
    
    joblib.dump(xgboost_model, os.path.join(model_dir, "xgboost.joblib"))
    print(f"Saved XGBoost model to {model_dir}/xgboost.joblib")
    
    joblib.dump(risk_mapping, os.path.join(model_dir, "risk_mapping.joblib"))
    print(f"Saved risk mapping to {model_dir}/risk_mapping.joblib")
    
    feature_names = ['min_temp_c', 'avg_temp_c', 'wind_speed', 'humidity', 'wind_chill', 'mean_aqi']
    joblib.dump(feature_names, os.path.join(model_dir, "feature_names.joblib"))
    print(f"Saved feature names to {model_dir}/feature_names.joblib")


def train_models():
    try:
        if not all([db_user, db_password, db_host, db_name]):
            raise ValueError("Database credentials are required. Set DB_USER, DB_PASSWORD, DB_HOST, DB_NAME in .env")
        
        engine = create_engine(f"mysql+mysqlconnector://{db_user}:{db_password}@{db_host}/{db_name}")
        
        # Load training data
        X, y, risk_mapping, class_names = load_training_data(engine)
        
        # Train models
        logistic_model, scaler = train_logistic_regression(X, y, class_names)
        xgboost_model = train_xgboost(X, y, class_names)
        
        # Save models
        save_models(logistic_model, scaler, xgboost_model, risk_mapping)
        
        print("\nModel training completed successfully!")
        return True
        
    except Exception as e:
        print(f"\nError training models: {e}")
        return False


if __name__ == "__main__":
    train_models()

