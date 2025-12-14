import os
import numpy as np
import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client

from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.ensemble import GradientBoostingRegressor


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL/SUPABASE_KEY in env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def main():
    supabase = sb()

    print("Fetching locations with deep features...")
    resp = supabase.table("locations").select(
        "place_id,name,rating,user_ratings_total,price_level,types,avg_openai_sentiment,sd_openai_sentiment,avg_roberta_score,pct_dive_positive,rating_sd"
    ).execute()
    df = pd.DataFrame(resp.data)
    if df.empty:
        print("No locations found.")
        return

    # Basic cleaning
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").fillna(0.0)
    df["user_ratings_total"] = pd.to_numeric(df["user_ratings_total"], errors="coerce").fillna(0)
    df["price_level"] = pd.to_numeric(df["price_level"], errors="coerce").fillna(2)

    # Some locations won't have deep features if they had no reviews text/analysis early on
    for col in ["avg_openai_sentiment", "sd_openai_sentiment", "avg_roberta_score", "pct_dive_positive", "rating_sd"]:
        df[col] = pd.to_numeric(df.get(col), errors="coerce").fillna(0.0)

    df["log_reviews"] = np.log1p(df["user_ratings_total"])
    df["primary_type"] = df["types"].apply(lambda x: x[0] if isinstance(x, list) and len(x) > 0 else "establishment")

    features_num = [
        "log_reviews",
        "price_level",
        "avg_openai_sentiment",
        "sd_openai_sentiment",
        "avg_roberta_score",
        "pct_dive_positive",
        "rating_sd",
    ]
    features_cat = ["primary_type"]

    X = df[features_num + features_cat]
    y = df["rating"]

    pre = ColumnTransformer(
        transformers=[
            ("cat", OneHotEncoder(handle_unknown="ignore"), features_cat),
        ],
        remainder="passthrough",
    )

    # Use GradientBoostingRegressor because it supports sparse input from OneHotEncoder
    model = GradientBoostingRegressor(
        n_estimators=300,
        learning_rate=0.08,
        max_depth=4,
        random_state=42,
    )

    pipe = Pipeline([("pre", pre), ("model", model)])

    print("Training deep residual model...")
    pipe.fit(X, y)

    df["predicted_rating_deep"] = pipe.predict(X)
    df["residual_deep"] = df["rating"] - df["predicted_rating_deep"]

    top = df.sort_values("residual_deep", ascending=False).head(10)[
        ["name", "rating", "predicted_rating_deep", "residual_deep", "pct_dive_positive", "rating_sd"]
    ]
    print("\nTop 10 Deep Residual Gems:")
    print(top.to_string(index=False))

    print("\nSaving ml_metadata updates to locations...")
    batch_size = 50
    updates = []
    for _, r in df.iterrows():
        updates.append(
            {
                "place_id": r["place_id"],
                "ml_metadata": {
                    "model_version": "deep_v1",
                    "predicted_rating_deep": round(float(r["predicted_rating_deep"]), 3),
                    "residual_deep": round(float(r["residual_deep"]), 3),
                },
            }
        )

    for i in range(0, len(updates), batch_size):
        batch = updates[i : i + batch_size]
        for item in batch:
            supabase.table("locations").update({"ml_metadata": item["ml_metadata"]}).eq("place_id", item["place_id"]).execute()
        print(f"Updated batch {i//batch_size + 1}/{int(np.ceil(len(updates)/batch_size))}")

    print("Done.")


if __name__ == "__main__":
    main()


