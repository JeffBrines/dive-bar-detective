"""
Isolation Forest Anomaly Detection - Find "truly unique" places.
These are statistical outliers in the 9-signal space that defy categorization.
"""
import os
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Signal columns to use for anomaly detection
SIGNAL_COLUMNS = [
    "avg_food_drink_quality",
    "avg_service_quality", 
    "avg_value_score",
    "avg_divey_score",
    "avg_classic_institution",
    "avg_unpretentious",
    "avg_authenticity",
    "avg_would_recommend",
    "avg_memorable",
]


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_locations_with_signals() -> pd.DataFrame:
    """Fetch all locations with their NLP signal aggregates."""
    supabase = get_supabase_client()
    
    cols = ["place_id", "name"] + SIGNAL_COLUMNS
    resp = supabase.table("locations").select(",".join(cols)).execute()
    
    df = pd.DataFrame(resp.data)
    print(f"Fetched {len(df)} locations")
    return df


def detect_anomalies(df: pd.DataFrame, contamination: float = 0.1) -> pd.DataFrame:
    """
    Apply Isolation Forest to identify outliers in the signal space.
    Returns dataframe with place_id and anomaly_score.
    
    anomaly_score interpretation:
    - Negative values: Anomalies (more negative = more unusual)
    - Positive values: Normal points
    """
    # Extract feature matrix
    feature_df = df[SIGNAL_COLUMNS].copy()
    
    # Fill missing values with column median
    for col in SIGNAL_COLUMNS:
        median = feature_df[col].median()
        feature_df[col] = feature_df[col].fillna(median if pd.notna(median) else 0.5)
    
    X = feature_df.values
    print(f"Feature matrix shape: {X.shape}")
    
    # Fit Isolation Forest
    print(f"Fitting Isolation Forest (contamination={contamination})...")
    clf = IsolationForest(
        n_estimators=100,
        contamination=contamination,
        random_state=42,
        n_jobs=-1
    )
    
    # Fit the model
    clf.fit(X)
    
    # Get anomaly scores (decision_function returns raw scores)
    # More negative = more anomalous
    anomaly_scores = clf.decision_function(X)
    predictions = clf.predict(X)  # 1 = normal, -1 = anomaly
    
    # Count anomalies
    n_anomalies = (predictions == -1).sum()
    print(f"Detected {n_anomalies} anomalies ({n_anomalies/len(df)*100:.1f}%)")
    
    # Create result dataframe
    result = pd.DataFrame({
        "place_id": df["place_id"],
        "name": df["name"],
        "anomaly_score": anomaly_scores,
        "is_anomaly": predictions == -1
    })
    
    return result


def save_anomaly_scores_to_db(anomaly_df: pd.DataFrame, batch_size: int = 50):
    """Save anomaly scores to locations table."""
    supabase = get_supabase_client()
    
    records = anomaly_df.to_dict('records')
    total = len(records)
    
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        for rec in batch:
            supabase.table("locations").update({
                "anomaly_score": float(rec["anomaly_score"])
            }).eq("place_id", rec["place_id"]).execute()
        
        print(f"Updated {min(i+batch_size, total)}/{total} locations")
    
    print("Done saving anomaly scores!")


def main(contamination: float = 0.1):
    print("=== Isolation Forest Anomaly Detection ===\n")
    
    # Fetch data
    df = fetch_locations_with_signals()
    if df.empty:
        print("No locations found!")
        return
    
    # Check for missing signals
    missing_count = df[SIGNAL_COLUMNS].isna().sum().sum()
    if missing_count > 0:
        print(f"Note: {missing_count} missing signal values will be filled with medians")
    
    # Detect anomalies
    anomaly_df = detect_anomalies(df, contamination=contamination)
    
    # Show most unique places
    print("\n🌟 Top 10 Most Unique Places (lowest anomaly scores):")
    top_unique = anomaly_df.nsmallest(10, "anomaly_score")
    for _, row in top_unique.iterrows():
        status = "⭐ UNIQUE" if row["is_anomaly"] else ""
        print(f"  {row['name'][:40]:<42} score: {row['anomaly_score']:.3f} {status}")
    
    print("\n📊 Most Normal Places (highest anomaly scores):")
    most_normal = anomaly_df.nlargest(5, "anomaly_score")
    for _, row in most_normal.iterrows():
        print(f"  {row['name'][:40]:<42} score: {row['anomaly_score']:.3f}")
    
    # Save to database
    print("\nSaving to database...")
    save_anomaly_scores_to_db(anomaly_df)
    
    print("\n✅ Anomaly detection complete!")


if __name__ == "__main__":
    import sys
    contamination = 0.1
    if len(sys.argv) > 1:
        try:
            contamination = float(sys.argv[1])
        except ValueError:
            pass
    main(contamination=contamination)
