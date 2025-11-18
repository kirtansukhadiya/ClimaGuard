import joblib
import numpy as np
import pandas as pd
import shap
import os


def load_model_and_artifacts(model_type="xgboost", model_dir="models"):
    model_path = os.path.join(model_dir, f"{model_type}.joblib")
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found: {model_path}. Run train.py first.")
    
    model = joblib.load(model_path)
    
    scaler = None
    if model_type == "logistic":
        scaler_path = os.path.join(model_dir, "scaler.joblib")
        if os.path.exists(scaler_path):
            scaler = joblib.load(scaler_path)
    
    risk_mapping_path = os.path.join(model_dir, "risk_mapping.joblib")
    if not os.path.exists(risk_mapping_path):
        raise FileNotFoundError(f"Risk mapping not found: {risk_mapping_path}")
    risk_mapping = joblib.load(risk_mapping_path)
    
    feature_names_path = os.path.join(model_dir, "feature_names.joblib")
    if not os.path.exists(feature_names_path):
        feature_names = ['min_temp_c', 'avg_temp_c', 'wind_speed', 'humidity', 'wind_chill', 'mean_aqi']
    else:
        feature_names = joblib.load(feature_names_path)
    
    return model, scaler, risk_mapping, feature_names


def explain_prediction(features, model_type="xgboost", model_dir="models", top_n=3):
    try:
        model, scaler, risk_mapping, feature_names = load_model_and_artifacts(model_type, model_dir)
        
        if isinstance(features, dict):
            feature_array = np.array([[features.get(f, 0) for f in feature_names]])
        else:
            feature_array = np.array(features).reshape(1, -1)
        
        if model_type == "logistic" and scaler is not None:
            feature_array = scaler.transform(feature_array)
        
        prediction_proba = model.predict_proba(feature_array)[0]
        prediction_idx = np.argmax(prediction_proba)
        confidence = float(prediction_proba[prediction_idx])
        
        reverse_mapping = {v: k for k, v in risk_mapping.items()}
        predicted_risk = reverse_mapping.get(prediction_idx, "Unknown")
        
        if model_type == "xgboost":
            explainer = shap.TreeExplainer(model)
            shap_values_all = explainer.shap_values(feature_array)
            if isinstance(shap_values_all, list):
                shap_values = shap_values_all[prediction_idx][0]
            else:
                shap_values = shap_values_all[0]
        else:
            try:
                explainer = shap.LinearExplainer(model, feature_array)
                shap_values_all = explainer.shap_values(feature_array)
                if isinstance(shap_values_all, list):
                    shap_values = shap_values_all[prediction_idx][0]
                else:
                    shap_values = shap_values_all[0]
            except Exception:
                if hasattr(model, 'coef_'):
                    coef = model.coef_[prediction_idx]
                    shap_values = (coef * feature_array[0])
                else:
                    shap_values = np.ones(len(feature_names)) / len(feature_names)
        
        shap_abs = np.abs(shap_values)
        
        top_indices = np.argsort(shap_abs)[::-1][:top_n]
        top_reasons = [feature_names[i] for i in top_indices]
        
        feature_importance = {
            feature_names[i]: float(shap_values[i])
            for i in range(len(feature_names))
        }
        
        return {
            'prediction': predicted_risk,
            'confidence': confidence,
            'top_reasons': top_reasons,
            'shap_values': feature_importance
        }
        
    except Exception as e:
        raise Exception(f"Error generating explanation: {e}")


def explain_batch(features_list, model_type="xgboost", model_dir="models"):
    explanations = []
    for features in features_list:
        try:
            explanation = explain_prediction(features, model_type, model_dir)
            explanations.append(explanation)
        except Exception as e:
            print(f"Error explaining prediction: {e}")
            explanations.append(None)
    
    return explanations


if __name__ == "__main__":
    import sys
    
    example_features = {
        'min_temp_c': -5.0,
        'avg_temp_c': 2.0,
        'wind_speed': 5.0,
        'humidity': 75.0,
        'wind_chill': -8.0,
        'mean_aqi': 3.0
    }
    
    try:
        explanation = explain_prediction(example_features, model_type="xgboost")
        print("\nPrediction Explanation:")
        print(f"Predicted Risk: {explanation['prediction']}")
        print(f"Confidence: {explanation['confidence']:.4f}")
        print(f"\nTop Contributing Factors:")
        for i, reason in enumerate(explanation['top_reasons'], 1):
            shap_val = explanation['shap_values'][reason]
            print(f"{i}. {reason}: {shap_val:.4f}")
    except Exception as e:
        print(f"Error: {e}")
        print("Make sure models are trained (run train.py first)")

