import os
import pandas as pd
import numpy as np
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def calculate_sd():
    print("Calculating Rating Standard Deviation...")
    supabase = get_supabase_client()
    
    # 1. Fetch all reviews
    # We need to calculate SD per place_id
    # Since downloading all 4000+ reviews is fast, let's do it in memory.
    # For larger datasets, we'd do this in SQL or batches.
    
    print("Fetching reviews...")
    rows = []
    page_size = 1000
    offset = 0
    while True:
        response = supabase.table("reviews").select("place_id, openai_sentiment").range(offset, offset + page_size - 1).execute()
        batch = response.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        print(f"  fetched {len(rows)} reviews...")

    reviews_df = pd.DataFrame(rows)
    
    if reviews_df.empty:
        print("No reviews found.")
        return

    # 2. Group by place_id and calculate std (using openai_sentiment as proxy, since per-review star rating isn't present)
    stats = reviews_df.groupby('place_id')['openai_sentiment'].agg(['std', 'count']).reset_index()
    stats.columns = ['place_id', 'rating_sd', 'review_count']
    
    # Fill NaN (places with 1 review have undefined SD) with 0
    stats['rating_sd'] = stats['rating_sd'].fillna(0)
    
    print(f"Calculated SD for {len(stats)} locations.")
    print("Top 5 Highest Variance Locations:")
    print(stats.sort_values('rating_sd', ascending=False).head(5))
    
    # 3. Update locations table
    print("Updating locations table...")
    
    updates = []
    for _, row in stats.iterrows():
        updates.append({
            "place_id": row['place_id'],
            "rating_sd": round(row['rating_sd'], 3)
        })
        
    # Batch update
    batch_size = 50
    for i in range(0, len(updates), batch_size):
        batch = updates[i:i+batch_size]
        try:
            for item in batch:
                supabase.table("locations").update({"rating_sd": item["rating_sd"]}).eq("place_id", item["place_id"]).execute()
            print(f"Updated batch {i//batch_size + 1}")
        except Exception as e:
            print(f"Error updating batch: {e}")

if __name__ == "__main__":
    calculate_sd()

