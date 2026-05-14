import os
import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

def train_synthetic_classifier():
    print("Generating synthetic dataset for Document Classification...")
    
    # Synthetic data covering 6 categories
    data = [
        {"text": "Consolidated Unaudited Financial Results for the Quarter and Nine Months Ended", "label": "Quarterly Results"},
        {"text": "Statement of Standalone Unaudited Financial Results for the Quarter Ended 31st December", "label": "Quarterly Results"},
        {"text": "Q3 FY24 Earnings Release and Financials", "label": "Quarterly Results"},
        
        {"text": "Audited Standalone and Consolidated Financial Results for the year ended 31st March", "label": "Annual Results"},
        {"text": "Annual Report and Financial Statements 2025-2026", "label": "Annual Results"},
        {"text": "Statement of Audited Financial Results for the Year Ended", "label": "Annual Results"},
        
        {"text": "Declaration of Interim Dividend for the Financial Year", "label": "Dividend Notice"},
        {"text": "Intimation of Record Date for payment of Final Dividend", "label": "Dividend Notice"},
        
        {"text": "Outcome of Board Meeting held on today", "label": "Board Meeting Outcome"},
        {"text": "The Board of Directors at their meeting held today approved the resignation of", "label": "Board Meeting Outcome"},
        
        {"text": "Investor Presentation Q4 FY26 Earnings Call", "label": "Investor Presentation"},
        {"text": "Corporate Presentation highlighting business performance and growth strategy", "label": "Investor Presentation"},
        
        {"text": "Notice of Postal Ballot to the Shareholders", "label": "Other"},
        {"text": "Intimation regarding Loss of Share Certificate", "label": "Other"},
    ]
    
    df = pd.DataFrame(data)
    
    pipeline = Pipeline([
        ('tfidf', TfidfVectorizer(ngram_range=(1, 2))),
        ('clf', LogisticRegression(random_state=42))
    ])
    
    print("Training pipeline...")
    pipeline.fit(df['text'], df['label'])
    
    accuracy = pipeline.score(df['text'], df['label'])
    print(f"Training Accuracy on synthetic data: {accuracy * 100:.2f}%")
    
    # Save the model
    os.makedirs("app/ml_models", exist_ok=True)
    model_path = "app/ml_models/doc_classifier.joblib"
    joblib.dump(pipeline, model_path)
    print(f"Model saved to {model_path}")

if __name__ == "__main__":
    train_synthetic_classifier()
