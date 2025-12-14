import os
import math
import json
from collections import Counter

import pandas as pd
from dotenv import load_dotenv
from supabase import create_client, Client


load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def sb() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise RuntimeError("Missing SUPABASE_URL/SUPABASE_KEY in env")
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def compute_top_keywords(rows: pd.DataFrame, k: int = 8) -> dict:
    # rows has a column openai_keywords which is list[str] or None
    counter: Counter[str] = Counter()
    for kw_list in rows.get("openai_keywords", []):
        if not kw_list:
            continue
        for kw in kw_list:
            if not kw:
                continue
            s = str(kw).strip().lower()
            if not s:
                continue
            counter[s] += 1
    return dict(counter.most_common(k))


def main():
    supabase = sb()

    print("Fetching reviews with all signals...")
    # Supabase PostgREST defaults to returning a limited page of rows.
    # We must paginate to fetch the whole dataset.
    rows = []
    page_size = 1000
    offset = 0
    select_cols = (
        "place_id, roberta_score, openai_sentiment, openai_is_dive_positive, openai_keywords, "
        "food_drink_quality, service_quality, value_score, divey_score, classic_institution, "
        "unpretentious, authenticity, would_recommend, memorable"
    )
    while True:
        resp = (
            supabase.table("reviews")
            .select(select_cols)
            .range(offset, offset + page_size - 1)
            .execute()
        )
        batch = resp.data or []
        if not batch:
            break
        rows.extend(batch)
        offset += page_size
        print(f"  fetched {len(rows)} reviews...")

    df = pd.DataFrame(rows)
    if df.empty:
        print("No review rows found.")
        return

    # Normalize missing values
    df["openai_sentiment"] = pd.to_numeric(df["openai_sentiment"], errors="coerce")
    df["roberta_score"] = pd.to_numeric(df["roberta_score"], errors="coerce")
    df["openai_is_dive_positive"] = df["openai_is_dive_positive"].fillna(False).astype(bool)

    # New rich signals
    new_signal_cols = [
        "food_drink_quality", "service_quality", "value_score", "divey_score",
        "classic_institution", "unpretentious", "authenticity", "would_recommend", "memorable"
    ]
    for col in new_signal_cols:
        df[col] = pd.to_numeric(df.get(col), errors="coerce")

    print(f"Computing per-location aggregates for {df['place_id'].nunique()} locations...")

    grouped = df.groupby("place_id", dropna=False)

    out_rows = []
    for place_id, g in grouped:
        if not isinstance(place_id, str) or not place_id:
            continue

        avg_openai = float(g["openai_sentiment"].mean(skipna=True)) if g["openai_sentiment"].notna().any() else 0.0
        sd_openai = float(g["openai_sentiment"].std(ddof=1, skipna=True)) if g["openai_sentiment"].notna().sum() >= 2 else 0.0
        avg_roberta = float(g["roberta_score"].mean(skipna=True)) if g["roberta_score"].notna().any() else 0.0
        review_count = int(len(g))
        dive_positive_count = int(g["openai_is_dive_positive"].sum())
        pct_dive = float(g["openai_is_dive_positive"].mean())  # 0..1
        top_kw = compute_top_keywords(g, k=10)

        # Aggregate new signals
        def avg_col(col_name):
            return float(g[col_name].mean(skipna=True)) if g[col_name].notna().any() else 0.5

        out_rows.append(
            {
                "place_id": place_id,
                "avg_openai_sentiment": round(avg_openai, 4),
                "sd_openai_sentiment": round(sd_openai, 4),
                "avg_roberta_score": round(avg_roberta, 4),
                "pct_dive_positive": round(pct_dive, 4),
                "review_count": review_count,
                "dive_positive_count": dive_positive_count,
                "top_keywords": top_kw,
                # New rich signal aggregates
                "avg_food_drink_quality": round(avg_col("food_drink_quality"), 4),
                "avg_service_quality": round(avg_col("service_quality"), 4),
                "avg_value_score": round(avg_col("value_score"), 4),
                "avg_divey_score": round(avg_col("divey_score"), 4),
                "avg_classic_institution": round(avg_col("classic_institution"), 4),
                "avg_unpretentious": round(avg_col("unpretentious"), 4),
                "avg_authenticity": round(avg_col("authenticity"), 4),
                "avg_would_recommend": round(avg_col("would_recommend"), 4),
                "avg_memorable": round(avg_col("memorable"), 4),
            }
        )

    print(f"Updating {len(out_rows)} location rows...")

    # Update locations in batches
    batch_size = 50
    for i in range(0, len(out_rows), batch_size):
        batch = out_rows[i : i + batch_size]
        for item in batch:
            supabase.table("locations").update(
                {
                    "avg_openai_sentiment": item["avg_openai_sentiment"],
                    "sd_openai_sentiment": item["sd_openai_sentiment"],
                    "avg_roberta_score": item["avg_roberta_score"],
                    "pct_dive_positive": item["pct_dive_positive"],
                    "review_count": item["review_count"],
                    "dive_positive_count": item["dive_positive_count"],
                    "top_keywords": item["top_keywords"],
                    # New rich signal aggregates
                    "avg_food_drink_quality": item["avg_food_drink_quality"],
                    "avg_service_quality": item["avg_service_quality"],
                    "avg_value_score": item["avg_value_score"],
                    "avg_divey_score": item["avg_divey_score"],
                    "avg_classic_institution": item["avg_classic_institution"],
                    "avg_unpretentious": item["avg_unpretentious"],
                    "avg_authenticity": item["avg_authenticity"],
                    "avg_would_recommend": item["avg_would_recommend"],
                    "avg_memorable": item["avg_memorable"],
                }
            ).eq("place_id", item["place_id"]).execute()
        print(f"Updated batch {i//batch_size + 1}/{math.ceil(len(out_rows)/batch_size)}")

    print("Done.")


if __name__ == "__main__":
    main()


