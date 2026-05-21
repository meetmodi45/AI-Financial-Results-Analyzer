import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report

def generate_synthetic_data(num_samples=1500):
    np.random.seed(42)
    
    # Generate realistic financial metrics
    qoq_growth = np.random.normal(loc=2.0, scale=15.0, size=num_samples)
    yoy_growth = np.random.normal(loc=5.0, scale=20.0, size=num_samples)
    net_margin = np.random.normal(loc=12.0, scale=10.0, size=num_samples)
    
    # Calculate a proxy "Earnings Strength" based purely on math
    earnings_strength = (qoq_growth * 0.4) + (yoy_growth * 0.4) + (net_margin * 0.2) + np.random.normal(0, 5, num_samples)
    
    df = pd.DataFrame({
        'qoq_growth': qoq_growth,
        'yoy_growth': yoy_growth,
        'net_margin': net_margin,
        'earnings_strength': earnings_strength
    })
    
    # Target rules (with some noise)
    conditions = [
        (df['earnings_strength'] > 10) & (df['yoy_growth'] > 5),
        (df['earnings_strength'] < -5) | (df['net_margin'] < 0)
    ]
    choices = ['GOOD', 'BAD']
    df['verdict'] = np.select(conditions, choices, default='NEUTRAL')
    
    return df

def train_and_save_model():
    print("Generating synthetic financial dataset (Quantitative Only)...")
    df = generate_synthetic_data(2000)
    print(df['verdict'].value_counts())
    
    X = df[['qoq_growth', 'yoy_growth', 'net_margin', 'earnings_strength']]
    y = df['verdict']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    print("Training Random Forest Ensemble Classifier...")
    model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    model.fit(X_train, y_train)
    
    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nModel Accuracy on Test Set: {acc * 100:.2f}%")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))
    
    # Ensure directory exists
    os.makedirs('app/ml_models', exist_ok=True)
    model_path = 'app/ml_models/verdict_classifier.joblib'
    
    joblib.dump(model, model_path)
    print(f"\nModel saved successfully to {model_path}")

if __name__ == "__main__":
    train_and_save_model()
