import os
import pandas as pd
import numpy as np
from supabase import create_client, Client
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import OneHotEncoder
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def train_and_score():
    print("Training 'True Rating' Model...")
    supabase = get_supabase_client()
    
    # 1. Fetch Data
    # We need locations and their 'structural' features
    response = supabase.table("locations").select("*").execute()
    df = pd.DataFrame(response.data)
    
    if df.empty:
        print("No data to train on.")
        return

    # 2. Preprocessing
    # Features: User Ratings Count (Log), Price Level, Types (Simplified)
    # Target: Rating
    
    # Fill NAs
    df['user_ratings_total'] = df['user_ratings_total'].fillna(0)
    df['price_level'] = df['price_level'].fillna(2) # Assume moderate if unknown
    df['rating'] = df['rating'].fillna(0)
    
    # Feature Engineering
    df['log_reviews'] = np.log1p(df['user_ratings_total'])
    
    # Simplified Type (Take first type)
    df['primary_type'] = df['types'].apply(lambda x: x[0] if x and len(x) > 0 else 'establishment')
    
    # Define Features
    features = ['log_reviews', 'price_level', 'primary_type']
    target = 'rating'
    
    X = df[features]
    y = df[target]
    
    # 3. Model Pipeline
    preprocessor = ColumnTransformer(
        transformers=[
            ('cat', OneHotEncoder(handle_unknown='ignore'), ['primary_type']),
            # Numerical features are passed through
        ],
        remainder='passthrough'
    )
    
    pipeline = Pipeline([
        ('preprocessor', preprocessor),
        ('regressor', GradientBoostingRegressor(n_estimators=100, random_state=42))
    ])
    
    # 4. Train
    pipeline.fit(X, y)
    
    # 5. Predict & Calculate Residuals
    df['predicted_rating'] = pipeline.predict(X)
    df['residual'] = df['rating'] - df['predicted_rating']
    
    # Positive Residual = Rated higher than algorithm expects (Overperforming / Gem)
    # Negative Residual = Rated lower than expected (Underperforming)
    
    print("Top 5 Overperforming Gems (High Positive Residual):")
    print(df.sort_values('residual', ascending=False)[['name', 'rating', 'predicted_rating', 'residual']].head(5))
    
    # 6. Save Scores back to DB (Batch Update)
    # Ideally we'd add columns for this, but for now we can just store it in a new 'ml_scores' jsonb column or update existing rows
    # Let's assume we add a 'ml_metadata' jsonb column to locations
    
    # For now, let's just print them. In a real app, we'd upsert these.
    # To make this actionable, let's enable an upsert loop
    
    updates = []
    for _, row in df.iterrows():
        updates.append({
            "place_id": row['place_id'],
            "ml_metadata": {
                "predicted_rating": round(row['predicted_rating'], 2),
                "residual": round(row['residual'], 2),
                "model_version": "v1"
            }
        })
        
    # Chunk updates to avoid payload limits
    batch_size = 50
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        try:
            # We are upserting. Since place_id is PK, this updates the row.
            # However, we need to pass ALL required columns or use a PATCH method if the library supports partial updates easily.
            # Supabase-py 'upsert' usually replaces the row or requires all non-nullable fields if it's a new row.
            # But for existing rows, we might need a different approach if we don't want to re-send everything.
            # Actually, let's just use 'update' per row for safety in this prototype, or carefully construct upsert.
            
            # For massive efficiency, upsert is better, but let's just loop update for safety now.
            for item in batch:
                supabase.table("locations").update({"ml_metadata": item["ml_metadata"]}).eq("place_id", item["place_id"]).execute()
                
            print(f"Updated batch {i//batch_size + 1}")
        except Exception as e:
            print(f"Error updating batch: {e}")
        
    return df

if __name__ == "__main__":
    train_and_score()

