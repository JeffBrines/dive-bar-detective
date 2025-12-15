import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL/SUPABASE_KEY in env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def tag_row(r: pd.Series) -> str:
    # Simple interpretable rule mapping after clustering.
    # We’ll label with heuristics based on the features rather than cluster index.
    if r["pct_dive_positive"] >= 0.35 and r["rating_sd"] >= 1.2:
        return "Polarizing_Dive"
    if r["pct_dive_positive"] >= 0.35 and r["rating_sd"] < 1.2:
        return "Beloved_Dive"
    if r["avg_openai_sentiment"] >= 0.55 and r["sd_openai_sentiment"] < 0.35:
        return "Consistent_Gem"
    if r["avg_openai_sentiment"] < 0.1 and r["sd_openai_sentiment"] >= 0.5:
        return "Messy_Mixed"
    return "Other"


def main():
    supabase = sb()
    print("Fetching locations for clustering...")
    resp = supabase.table("locations").select(
        "place_id,name,avg_openai_sentiment,sd_openai_sentiment,avg_roberta_score,pct_dive_positive,rating_sd"
    ).execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        print("No locations found.")
        return

    for col in ["avg_openai_sentiment", "sd_openai_sentiment", "avg_roberta_score", "pct_dive_positive", "rating_sd"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)

    # Only cluster rows that actually have some computed sentiment
    mask = (df["avg_openai_sentiment"] != 0.0) | (df["avg_roberta_score"] != 0.0)
    dfx = df[mask].copy()
    if dfx.empty:
        print("No feature-rich locations to cluster.")
        return

    features = ["avg_openai_sentiment", "sd_openai_sentiment", "pct_dive_positive", "rating_sd"]
    X = dfx[features].to_numpy()

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    k = 4
    km = KMeans(n_clusters=k, random_state=42, n_init=20)
    dfx["vibe_cluster"] = km.fit_predict(Xs).astype(int)

    # Human-friendly tag per row (rule-based)
    dfx["vibe_tag"] = dfx.apply(tag_row, axis=1)

    print("Cluster counts:")
    print(dfx["vibe_cluster"].value_counts().sort_index().to_string())
    print("\nTop tag counts:")
    print(dfx["vibe_tag"].value_counts().to_string())

    # Persist to DB
    updates = dfx[["place_id", "vibe_cluster", "vibe_tag"]].to_dict(orient="records")
    batch_size = 50
    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        for item in batch:
            supabase.table("locations").update(
                {"vibe_cluster": int(item["vibe_cluster"]), "vibe_tag": item["vibe_tag"]}
            ).eq("place_id", item["place_id"]).execute()
        print(f"Updated batch {i//batch_size + 1}/{int(np.ceil(len(updates)/batch_size))}")

    print("Done.")


if __name__ == "__main__":
    main()



