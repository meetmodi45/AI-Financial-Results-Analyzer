import os
import joblib
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier

def train_synthetic_verdict_model():
    print("Generating synthetic dataset for Verdict Prediction...")
    
    # Features: [qoq_growth, yoy_growth, net_margin, earnings_strength]
    np.random.seed(42)
    num_samples = 500
    
    qoq = np.random.normal(loc=2.0, scale=10.0, size=num_samples)
    yoy = np.random.normal(loc=8.0, scale=15.0, size=num_samples)
    margin = np.random.normal(loc=12.0, scale=8.0, size=num_samples)
    strength = np.random.randint(20, 100, size=num_samples)
    
    # Rule-based synthetic labeling to train the model
    labels = []
    for i in range(num_samples):
        if yoy[i] > 10 and margin[i] > 15:
            labels.append("GOOD")
        elif yoy[i] < 0 or margin[i] < 0:
            labels.append("BAD")
        else:
            labels.append("NEUTRAL")
            
    df = pd.DataFrame({
        'qoq_growth': qoq,
        'yoy_growth': yoy,
        'net_margin': margin,
        'earnings_strength': strength,
        'label': labels
    })
    
    clf = RandomForestClassifier(n_estimators=100, random_state=42)
    X = df[['qoq_growth', 'yoy_growth', 'net_margin', 'earnings_strength']]
    y = df['label']
    
    print("Training Random Forest Classifier...")
    clf.fit(X, y)
    
    accuracy = clf.score(X, y)
    print(f"Training Accuracy on synthetic data: {accuracy * 100:.2f}%")
    
    # Save the model
    os.makedirs("app/ml_models", exist_ok=True)
    model_path = "app/ml_models/verdict_classifier.joblib"
    joblib.dump(clf, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_synthetic_verdict_model()
