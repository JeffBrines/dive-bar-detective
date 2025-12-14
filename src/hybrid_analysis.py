import os
import time
from typing import List, Dict
import pandas as pd
from transformers import pipeline
from openai import OpenAI
from supabase import create_client, Client
from dotenv import load_dotenv
import json
import random
import httpx

load_dotenv()

# Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-nano")

if not OPENAI_API_KEY:
    print("Warning: OPENAI_API_KEY not found.")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# 1. RoBERTa Setup (DISABLED for speed - OpenAI provides sentiment)
# print("Loading RoBERTa...")
# roberta_pipeline = pipeline("sentiment-analysis", model="cardiffnlp/twitter-roberta-base-sentiment", truncation=True, max_length=512)

# 2. OpenAI Setup
client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """You are a "Dive Bar Sommelier" analyzing reviews to identify great dive bars, hidden gems, and local favorites.

For each review, extract these signals. All scores are floats from 0.0 to 1.0 unless noted otherwise.

**Quality Signals**
- "food_drink_quality": How good is the food/drinks? (0=terrible, 1=exceptional)
- "service_quality": Staff friendliness, attentiveness (0=rude/slow, 1=amazing)
- "value_score": Bang for buck, fair pricing (0=overpriced, 1=great deal)

**Vibe Signals**
- "divey_score": Gritty dive bar energy — cheap, cash-only, sticky floors, no-frills, hole-in-wall (0=none, 1=maximum dive)
- "classic_institution": Long-running, retro, "been here forever", neighborhood staple (0=new/generic, 1=beloved institution)
- "unpretentious": Come-as-you-are, laid-back, no dress code, regulars welcome (0=fancy/uptight, 1=totally chill)
- "authenticity": Genuine character, soul, not corporate/chain-like (0=generic, 1=one-of-a-kind)

**Experience Signals**
- "would_recommend": Does reviewer seem like they'd recommend this? (0=no, 1=enthusiastically)
- "memorable": Unique, special, stands out (0=forgettable, 1=unforgettable)

**Legacy Signals (keep for compatibility)**
- "sentiment_score": Overall sentiment (-1.0 to 1.0). Context matters: "It's a dump, I love it" = 0.8
- "is_dive_positive": Boolean. True if reviewer appreciates dive-bar OR classic-casual vibes (gritty charm, retro feel, laid-back, no pretense, regulars, neighborhood spot). NOT just "casual dining" — must have character.
- "keywords": List of 3-5 key vibes (e.g., "cheap", "local", "best burger", "institution", "hidden gem").

Output JSON only. If a signal isn't clearly mentioned, estimate based on overall tone or use 0.5 (neutral).
"""

def analyze_review_roberta(text: str) -> float:
    try:
        # Returns LABEL_0 (Neg), LABEL_1 (Neu), LABEL_2 (Pos)
        result = roberta_pipeline(text[:512])[0]
        label = result['label']
        score = result['score']
        
        if label == "LABEL_0":
            return -1.0 * score
        elif label == "LABEL_2":
            return 1.0 * score
        else:
            return 0.0
    except:
        return 0.0

def analyze_review_openai(text: str) -> Dict:
    try:
        completion = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Review: {text}"}
            ],
            response_format={"type": "json_object"}
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        print(f"OpenAI Error: {e}")
        return {"sentiment_score": 0.0, "is_dive_positive": False, "keywords": []}

def normalize_keywords(val) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(x)[:80] for x in val][:5]
    # Sometimes models return a comma-separated string
    if isinstance(val, str):
        parts = [p.strip() for p in val.split(",") if p.strip()]
        return [p[:80] for p in parts][:5]
    return []

def process_reviews(limit: int | None = None, batch_size: int = 50, sleep_s: float = 0.15):
    supabase = get_supabase_client()
    
    print(f"Processing reviews with OPENAI_MODEL={OPENAI_MODEL}")

    def supabase_update_with_retry(review_id: str, payload: dict, max_attempts: int = 6) -> None:
        """
        Supabase occasionally drops connections under sustained write load.
        This retries transient transport errors with exponential backoff + jitter.
        """
        for attempt in range(1, max_attempts + 1):
            try:
                supabase.table("reviews").update(payload).eq("id", review_id).execute()
                return
            except (httpx.ReadError, httpx.WriteError, httpx.ConnectError, httpx.RemoteProtocolError, httpx.TimeoutException) as e:
                if attempt == max_attempts:
                    raise
                backoff = min(30.0, (2 ** (attempt - 1)) * 0.5) + random.random() * 0.25
                print(f"Supabase transient error ({type(e).__name__}) on attempt {attempt}/{max_attempts}; sleeping {backoff:.2f}s")
                time.sleep(backoff)
            except Exception:
                # Non-transport errors: re-raise (likely schema/validation)
                raise

    processed = 0
    offset = 0

    # We page through the table. For larger datasets we'd want keyset pagination, but 4k rows is fine.
    while True:
        q = supabase.table("reviews").select("id, review_text").is_("analyzed_at", "null").range(offset, offset + batch_size - 1)
        if limit is not None:
            remaining = limit - processed
            if remaining <= 0:
                break
            q = q.limit(min(batch_size, remaining))

        resp = q.execute()
        batch = resp.data or []
        if not batch:
            break

        for review in batch:
            rid = review.get("id")
            text = (review.get("review_text") or "").strip()
            if not rid or not text:
                # Mark empty rows as analyzed to avoid looping forever
                supabase.table("reviews").update({"analyzed_at": "now()"}).eq("id", rid).execute()
                processed += 1
                continue

            print(f"Processing {rid}: {text[:60]}...")

            # RoBERTa disabled for speed - OpenAI provides sentiment
            roberta_score = None
            openai_analysis = analyze_review_openai(text)

            openai_sent = float(openai_analysis.get("sentiment_score", 0.0) or 0.0)
            openai_dive = bool(openai_analysis.get("is_dive_positive", False))
            openai_keywords = normalize_keywords(openai_analysis.get("keywords"))

            # New rich signals (0.0-1.0)
            food_drink_quality = float(openai_analysis.get("food_drink_quality", 0.5) or 0.5)
            service_quality = float(openai_analysis.get("service_quality", 0.5) or 0.5)
            value_score = float(openai_analysis.get("value_score", 0.5) or 0.5)
            divey_score = float(openai_analysis.get("divey_score", 0.0) or 0.0)
            classic_institution = float(openai_analysis.get("classic_institution", 0.0) or 0.0)
            unpretentious = float(openai_analysis.get("unpretentious", 0.5) or 0.5)
            authenticity = float(openai_analysis.get("authenticity", 0.5) or 0.5)
            would_recommend = float(openai_analysis.get("would_recommend", 0.5) or 0.5)
            memorable = float(openai_analysis.get("memorable", 0.5) or 0.5)

            supabase_update_with_retry(rid, {
                "roberta_score": roberta_score,
                "openai_sentiment": openai_sent,
                "openai_is_dive_positive": openai_dive,
                "openai_keywords": openai_keywords,
                "openai_model": OPENAI_MODEL,
                "analyzed_at": "now()",
                # New rich signals
                "food_drink_quality": food_drink_quality,
                "service_quality": service_quality,
                "value_score": value_score,
                "divey_score": divey_score,
                "classic_institution": classic_institution,
                "unpretentious": unpretentious,
                "authenticity": authenticity,
                "would_recommend": would_recommend,
                "memorable": memorable,
            })

            processed += 1
            if limit is not None and processed >= limit:
                break

            time.sleep(sleep_s)

        if limit is not None and processed >= limit:
            break

        # Do not increase offset when filtering analyzed_at IS NULL; range is over that filtered set.
        # Just keep fetching the "first page" until exhausted.
        offset = 0

    print(f"Done. Processed {processed} reviews.")
    
if __name__ == "__main__":
    process_reviews(limit=None, batch_size=25, sleep_s=0.2)

