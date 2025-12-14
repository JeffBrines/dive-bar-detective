"""
UMAP Visualization - Reduce 9 NLP signals to 2D for interactive exploration.
Creates a "vibe map" where similar places cluster together.
"""
import os
import numpy as np
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Signal columns to use for UMAP
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


def generate_umap_coordinates(df: pd.DataFrame, n_neighbors: int = 15, min_dist: float = 0.1) -> pd.DataFrame:
    """
    Apply UMAP to reduce 9-signal space to 2D.
    Returns dataframe with place_id, umap_x, umap_y.
    """
    try:
        import umap
    except ImportError:
        print("umap-learn not installed. Run: pip install umap-learn")
        return pd.DataFrame()
    
    # Extract feature matrix
    feature_df = df[SIGNAL_COLUMNS].copy()
    
    # Fill missing values with column median
    for col in SIGNAL_COLUMNS:
        median = feature_df[col].median()
        feature_df[col] = feature_df[col].fillna(median if pd.notna(median) else 0.5)
    
    X = feature_df.values
    print(f"Feature matrix shape: {X.shape}")
    
    # Fit UMAP
    print("Fitting UMAP...")
    reducer = umap.UMAP(
        n_components=2,
        n_neighbors=n_neighbors,
        min_dist=min_dist,
        metric='euclidean',
        random_state=42
    )
    embedding = reducer.fit_transform(X)
    print("UMAP complete!")
    
    # Create result dataframe
    result = pd.DataFrame({
        "place_id": df["place_id"],
        "umap_x": embedding[:, 0],
        "umap_y": embedding[:, 1]
    })
    
    return result


def save_umap_to_db(umap_df: pd.DataFrame, batch_size: int = 50):
    """Save UMAP coordinates to locations table."""
    supabase = get_supabase_client()
    
    records = umap_df.to_dict('records')
    total = len(records)
    
    for i in range(0, total, batch_size):
        batch = records[i:i+batch_size]
        for rec in batch:
            supabase.table("locations").update({
                "umap_x": float(rec["umap_x"]),
                "umap_y": float(rec["umap_y"])
            }).eq("place_id", rec["place_id"]).execute()
        
        print(f"Updated {min(i+batch_size, total)}/{total} locations")
    
    print("Done saving UMAP coordinates!")


def main():
    print("=== UMAP Visualization Generator ===\n")
    
    # Fetch data
    df = fetch_locations_with_signals()
    if df.empty:
        print("No locations found!")
        return
    
    # Check for missing signals
    missing_count = df[SIGNAL_COLUMNS].isna().sum().sum()
    if missing_count > 0:
        print(f"Note: {missing_count} missing signal values will be filled with medians")
    
    # Generate UMAP
    umap_df = generate_umap_coordinates(df)
    if umap_df.empty:
        return
    
    # Print some stats
    print(f"\nUMAP coordinate ranges:")
    print(f"  X: [{umap_df['umap_x'].min():.2f}, {umap_df['umap_x'].max():.2f}]")
    print(f"  Y: [{umap_df['umap_y'].min():.2f}, {umap_df['umap_y'].max():.2f}]")
    
    # Save to database
    print("\nSaving to database...")
    save_umap_to_db(umap_df)
    
    print("\n✅ UMAP visualization complete!")


if __name__ == "__main__":
    main()
