from fastapi import FastAPI, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from supabase import create_client, Client
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
from typing import List, Optional
import math
import datetime

load_dotenv()

app = FastAPI(title="Dive Bar Detective API")

# CORS Configuration - allow all origins for Replit proxy
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count"],
)

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def get_supabase() -> Client:
    """Get Supabase client, raising an error if not configured."""
    if supabase is None:
        raise HTTPException(status_code=503, detail="Supabase credentials not configured. Please set SUPABASE_URL and SUPABASE_KEY.")
    return supabase

class Location(BaseModel):
    place_id: str
    name: str
    address: Optional[str] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    rating: Optional[float] = None
    user_ratings_total: Optional[int] = None
    price_level: Optional[int] = None
    types: Optional[List[str]] = None
    formatted_phone_number: Optional[str] = None
    website: Optional[str] = None
    # Computed fields
    dive_score: Optional[float] = None
    dive_grade: Optional[str] = None
    gem_label: Optional[str] = None
    diveiness_0_10: Optional[float] = None  # Alias for character_0_10
    character_0_10: Optional[float] = None
    underrated_0_10: Optional[float] = None
    quality_0_10: Optional[float] = None
    blended_0_10: Optional[float] = None
    custom_score: Optional[float] = None  # Used by custom lens endpoint
    ml_metadata: Optional[dict] = None
    # Deep review aggregates
    avg_openai_sentiment: Optional[float] = None
    sd_openai_sentiment: Optional[float] = None
    avg_roberta_score: Optional[float] = None
    pct_dive_positive: Optional[float] = None
    rating_sd: Optional[float] = None
    vibe_cluster: Optional[int] = None
    vibe_tag: Optional[str] = None
    review_count: Optional[int] = None
    dive_positive_count: Optional[int] = None
    # New rich signal aggregates
    avg_food_drink_quality: Optional[float] = None
    avg_service_quality: Optional[float] = None
    avg_value_score: Optional[float] = None
    avg_divey_score: Optional[float] = None
    avg_classic_institution: Optional[float] = None
    avg_unpretentious: Optional[float] = None
    avg_authenticity: Optional[float] = None
    avg_would_recommend: Optional[float] = None
    avg_memorable: Optional[float] = None
    # ML-generated fields
    umap_x: Optional[float] = None
    umap_y: Optional[float] = None
    auto_tags: Optional[List[str]] = None
    anomaly_score: Optional[float] = None


class ReviewOut(BaseModel):
    id: str
    rating: Optional[int] = None
    review_text: Optional[str] = None
    author_name: Optional[str] = None
    openai_sentiment: Optional[float] = None
    openai_is_dive_positive: Optional[bool] = None

def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def _safe_float(x, default: float = 0.0) -> float:
    try:
        return float(x)
    except Exception:
        return default

def _safe_int(x, default: int = 0) -> int:
    try:
        return int(x)
    except Exception:
        return default

def _percentile_sorted(sorted_vals: List[float], pct: float) -> float:
    """
    Percentile of a pre-sorted list (0..100). Linear interpolation.
    """
    if not sorted_vals:
        return 0.0
    p = _clamp(float(pct), 0.0, 100.0) / 100.0
    if len(sorted_vals) == 1:
        return float(sorted_vals[0])
    idx = p * (len(sorted_vals) - 1)
    lo = int(math.floor(idx))
    hi = int(math.ceil(idx))
    if lo == hi:
        return float(sorted_vals[lo])
    w = idx - lo
    return float(sorted_vals[lo]) * (1.0 - w) + float(sorted_vals[hi]) * w


def normalize_to_percentile(places: List[dict], field: str, target_min: float = 2.0, target_max: float = 9.5) -> None:
    """
    Normalize a score field to percentile-based ranking within the dataset.
    Top place gets target_max, bottom gets target_min.
    This ensures all lenses have the same score distribution.
    """
    values = [(i, p.get(field)) for i, p in enumerate(places)]
    values = [(i, v) for i, v in values if isinstance(v, (int, float)) and not math.isnan(v)]
    
    if len(values) < 2:
        return
    
    values.sort(key=lambda x: x[1])
    n = len(values)
    for rank, (idx, _) in enumerate(values):
        percentile = rank / (n - 1)
        new_score = target_min + percentile * (target_max - target_min)
        places[idx][field] = round(new_score, 1)

def character_0_10(place: dict) -> Optional[float]:
    """
    Character score (0..10): Does this place have soul?
    Weights: authenticity 30%, classic 25%, unpretentious 20%, divey 15%, memorable 10%
    Falls back to pct_dive_positive if new signals aren't available.
    """
    auth = _safe_float(place.get("avg_authenticity"), None)
    classic = _safe_float(place.get("avg_classic_institution"), None)
    unpr = _safe_float(place.get("avg_unpretentious"), None)
    divey = _safe_float(place.get("avg_divey_score"), None)
    memo = _safe_float(place.get("avg_memorable"), None)

    if auth is not None and classic is not None and unpr is not None:
        # Use defaults for optional signals
        divey_val = divey if divey is not None else 0.0
        memo_val = memo if memo is not None else 0.5
        
        raw = 0.30 * auth + 0.25 * classic + 0.20 * unpr + 0.15 * divey_val + 0.10 * memo_val
        base = raw * 10.0  # Scale 0-1 to 0-10
    else:
        # Fallback to legacy pct_dive_positive with logistic mapping
        p = _safe_float(place.get("pct_dive_positive"), 0.0)
        p = _clamp(p, 0.0, 1.0)
        t = 0.28
        k = 16.0
        base = 10.0 / (1.0 + math.exp(-k * (p - t)))

    # Small vibe nudges
    vibe = place.get("vibe_tag")
    if vibe == "Beloved_Dive":
        base += 0.3
    elif vibe == "Polarizing_Dive":
        base += 0.2

    # Data guardrail: cap extremes when data is sparse
    gr = _safe_int(place.get("user_ratings_total"), 0)
    rc = _safe_int(place.get("review_count"), 0)
    if gr < 100 or rc < 25:
        base = min(base, 9.8)
    if gr < 50 or rc < 15:
        base = min(base, 9.4)

    return round(_clamp(base, 0.0, 10.0), 1)


def diveiness_0_10(place: dict) -> Optional[float]:
    """Alias for backwards compatibility - now called character_0_10"""
    return character_0_10(place)


def quality_0_10(place: dict) -> Optional[float]:
    """
    Quality score (0..10): Is it actually good?
    Weights: food 35%, recommend 30%, service 15%, value 10%, memorable 10%
    Falls back to avg_openai_sentiment if new signals aren't available.
    """
    food = _safe_float(place.get("avg_food_drink_quality"), None)
    service = _safe_float(place.get("avg_service_quality"), None)
    value = _safe_float(place.get("avg_value_score"), None)
    recommend = _safe_float(place.get("avg_would_recommend"), None)
    memo = _safe_float(place.get("avg_memorable"), None)

    if food is not None and recommend is not None:
        # Use defaults for optional signals
        svc = service if service is not None else 0.5
        val = value if value is not None else 0.5
        memo_val = memo if memo is not None else 0.5
        
        raw = 0.35 * food + 0.30 * recommend + 0.15 * svc + 0.10 * val + 0.10 * memo_val
        base = raw * 10.0  # Scale 0-1 to 0-10
    else:
        # Fallback to sentiment (scale from -1..1 to 0..10)
        sent = _safe_float(place.get("avg_openai_sentiment"), 0.0)
        base = (sent + 1.0) * 5.0  # -1 -> 0, 0 -> 5, 1 -> 10

    # Data guardrail
    gr = _safe_int(place.get("user_ratings_total"), 0)
    rc = _safe_int(place.get("review_count"), 0)
    if gr < 100 or rc < 25:
        base = min(base, 9.8)
    if gr < 50 or rc < 15:
        base = min(base, 9.4)

    return round(_clamp(base, 0.0, 10.0), 1)

def underrated_0_10(place: dict, *, scale: float = 0.35) -> Optional[float]:
    """
    Composite undervalued score (0..10): Is this better than Google suggests?
    - 40%: would_recommend exceeds normalized rating
    - 30%: sentiment exceeds normalized rating
    - 30%: inverse log of review count (less discovered)
    """
    recommend = _safe_float(place.get("avg_would_recommend"), None)
    sentiment = _safe_float(place.get("avg_openai_sentiment"), None)
    rating = _safe_float(place.get("rating"), 4.0)
    review_count = _safe_int(place.get("review_count"), 1)
    
    # If we don't have the new signals, fall back to ML residual
    if recommend is None or sentiment is None:
        ml_data = place.get("ml_metadata") or {}
        r = ml_data.get("residual_deep", None)
        if r is None:
            r = ml_data.get("residual", None)
        if r is None:
            return 5.0  # Neutral default
        r = _safe_float(r, 0.0)
        scale = max(0.10, float(scale))
        u = 5.0 + 5.0 * math.tanh(r / scale)
        return round(_clamp(u, 0.0, 10.0), 1)
    
    # Normalize rating to 0-1 scale (assuming 3.5-5.0 range)
    norm_rating = (rating - 3.5) / 1.5
    norm_rating = _clamp(norm_rating, 0.0, 1.0)
    
    # Normalize sentiment from -1..1 to 0..1
    norm_sentiment = (sentiment + 1.0) / 2.0
    
    # Recommend gap (positive = better than rating suggests)
    rec_gap = recommend - norm_rating
    
    # Sentiment gap
    sent_gap = norm_sentiment - norm_rating
    
    # Discovery factor (fewer reviews = more undiscovered)
    # log scale: 1 review = 1.0, 100 reviews = 0.5, 1000 = 0.25
    discovery = 1.0 / (1.0 + math.log10(max(review_count, 1)))
    
    # Combine (shift gaps to positive range, then blend)
    # rec_gap and sent_gap range from -1 to +1, shift to 0 to 1
    raw = 0.40 * (rec_gap + 1.0) / 2.0 + 0.30 * (sent_gap + 1.0) / 2.0 + 0.30 * discovery
    
    return round(_clamp(raw * 10.0, 0.0, 10.0), 1)

def blended_0_10(place: dict) -> Optional[float]:
    """
    Blended score (0..10): weighted average of quality, character, and underrated.
    - Quality (40%): Is it actually good?
    - Character (35%): Does it have soul?
    - Underrated (25%): Is it better than Google suggests?
    """
    q = place.get("quality_0_10")
    c = place.get("character_0_10")
    u = place.get("underrated_0_10")

    scores = []
    weights = []

    # Quality is most important (people want good places)
    if isinstance(q, (int, float)):
        scores.append(_safe_float(q))
        weights.append(0.40)

    # Character for the vibe/soul
    if isinstance(c, (int, float)):
        scores.append(_safe_float(c))
        weights.append(0.35)

    # Underrated for hidden gems
    if isinstance(u, (int, float)):
        scores.append(_safe_float(u))
        weights.append(0.25)

    if not scores:
        return None

    # Normalize weights if some scores are missing
    total_weight = sum(weights)
    weighted_sum = sum(s * w for s, w in zip(scores, weights))
    return round(weighted_sum / total_weight, 1)

def calculate_dive_score(place: dict) -> dict:
    """
    Calculates a 'Dive Score' (0-100) and assigns a label.
    Updated to use ML residuals if available.
    """
    rating = place.get("rating") or 0
    reviews = place.get("user_ratings_total") or 0
    price = place.get("price_level")
    
    # Check for ML metadata
    ml_data = place.get("ml_metadata") or {}
    # Support both legacy baseline model (v1) and deep model (deep_v1) keys.
    # UI and early code used `residual`; deep pipeline writes `residual_deep`.
    residual = ml_data.get("residual", None)
    if residual is None:
        residual = ml_data.get("residual_deep", 0)
    try:
        residual = float(residual)
    except Exception:
        residual = 0.0
    
    # 1. Rating Score (0-40)
    if rating >= 4.0:
        rating_score = 30 + ((rating - 4.0) * 10)
    elif rating >= 3.5:
        rating_score = 20 + ((rating - 3.5) * 20)
    else:
        rating_score = 10
    rating_score = min(40, rating_score)

    # 2. Review Count Score (0-30)
    if reviews < 20:
        review_score = 10
    elif 20 <= reviews <= 600:
        review_score = 30
    elif 600 < reviews <= 2000:
        review_score = 20
    else:
        review_score = 10

    # 3. Price Score (0-30)
    if price == 1: price_score = 30
    elif price == 2: price_score = 20
    elif price == 3: price_score = 5
    elif price == 4: price_score = 0
    else: price_score = 15

    # 4. ML Bonus (Up to +10 or -10)
    # If residual is > 0.2 (Overperforming), give a bonus
    ml_bonus = 0
    if residual > 0.3: ml_bonus = 10
    elif residual > 0.1: ml_bonus = 5
    elif residual < -0.3: ml_bonus = -5
    
    total_score = rating_score + review_score + price_score + ml_bonus
    total_score = max(0, min(100, total_score)) # Clamp
    
    # Coarse grade (less fake precision than 0-100)
    # A: gem, B: solid, C: decent, D: avoid
    if total_score >= 85:
        grade = "A"
    elif total_score >= 70:
        grade = "B"
    elif total_score >= 50:
        grade = "C"
    else:
        grade = "D"

    # Label
    if total_score >= 85:
        label = "💎 Certified Gem"
    elif total_score >= 70:
        label = "🍺 Solid Spot"
    elif total_score >= 50:
        label = "🤷 Decent"
    else:
        label = "🚫 Avoid"

    place["dive_score"] = round(total_score, 1)
    place["dive_grade"] = grade
    place["gem_label"] = label
    return place

def enrich_place(place: dict, *, underrated_scale: float = 0.35) -> dict:
    """
    Attach all computed fields used by frontend ranking and display.
    """
    place = calculate_dive_score(place)
    place["character_0_10"] = character_0_10(place)
    place["diveiness_0_10"] = place["character_0_10"]  # Alias for backwards compatibility
    place["quality_0_10"] = quality_0_10(place)
    place["underrated_0_10"] = underrated_0_10(place, scale=underrated_scale)
    place["blended_0_10"] = blended_0_10(place)  # Must come after character, quality, underrated
    return place

# Serve static files (frontend) from root directory
# This allows single-service deployment
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)))
if os.path.exists(os.path.join(static_dir, "index.html")):
    @app.get("/")
    async def serve_frontend():
        """Serve the main frontend HTML file"""
        return FileResponse(os.path.join(static_dir, "index.html"))
    
    # Mount static assets (if you have a static folder in the future)
    # app.mount("/static", StaticFiles(directory=os.path.join(static_dir, "static")), name="static")
else:
    @app.get("/")
    def read_root():
        return {"message": "Dive Bar Detective API - Ready to find gems."}

@app.get("/locations", response_model=List[Location])
def get_locations(
    response: Response,
    min_rating: float = Query(3.5, description="Minimum Google Rating"),
    min_reviews: int = Query(0, ge=0, description="Minimum Google review count"),
    kinds: Optional[List[str]] = Query(
        None,
        description="High-level place kinds to include (repeat param): bar, restaurant",
    ),
    kinds_mode: str = Query("any", enum=["any", "all"], description="Match any or all selected kinds"),
    sort_by: str = Query(
        "blended_0_10",
        enum=[
            "blended_0_10",
            "character_0_10",
            "diveiness_0_10",  # Alias for character_0_10
            "quality_0_10",
            "underrated_0_10",
            "rating",
            "user_ratings_total",
            "pct_dive_positive",
            "avg_openai_sentiment",
        ],
    ),
    limit: int = Query(120, ge=1, le=500, description="Max results returned"),
):
    try:
        db = get_supabase()
        query = db.table("locations").select("*").gte("rating", min_rating)
        
        # If max_price is specified and less than 4, filter
        # Note: we need to handle null prices (include them or exclude? Let's include them in general fetch but the UI can filter)
        # Supabase filter for OR is tricky in one line, so let's just fetch and filter in python for complex logic if needed.
        # For now, simplistic DB filtering:
        
        sb_resp = query.execute()
        results = sb_resp.data

        # Auto-calibrate underrated scale to make scores more "relative" within the current candidate set.
        abs_residuals: List[float] = []
        for p in results or []:
            md = p.get("ml_metadata") or {}
            r = md.get("residual_deep", None)
            if r is None:
                r = md.get("residual", None)
            if r is None:
                continue
            abs_residuals.append(abs(_safe_float(r, 0.0)))
        abs_residuals.sort()
        # Use p75 of |residual| as the scale so top results can reach the high end of 0–10.
        # Fallback to 0.20 if too little data.
        underrated_scale = _percentile_sorted(abs_residuals, 75) if len(abs_residuals) >= 10 else 0.20
        underrated_scale = max(0.10, float(underrated_scale))

        # Process and enrich
        enriched_results = [enrich_place(place, underrated_scale=underrated_scale) for place in results]
        
        # Normalize each lens to percentiles so all top out ~9.5
        normalize_to_percentile(enriched_results, "quality_0_10")
        normalize_to_percentile(enriched_results, "character_0_10")
        normalize_to_percentile(enriched_results, "underrated_0_10")
        
        # Recalculate blended after normalization
        for place in enriched_results:
            place["blended_0_10"] = blended_0_10(place)
        
        # Filter by min Google review count (in memory to handle nulls)
        if min_reviews and min_reviews > 0:
            enriched_results = [
                p for p in enriched_results
                if int(p.get("user_ratings_total") or 0) >= int(min_reviews)
            ]

        # Filter by high-level "kind" (bar/restaurant) based on Google place types
        KIND_TYPE_MAP = {
            "bar": {"bar", "night_club"},
            "restaurant": {"restaurant", "cafe", "meal_takeaway", "meal_delivery"},
        }

        def has_kind(p: dict, kind: str) -> bool:
            types = p.get("types") or []
            if not isinstance(types, list):
                return False
            want = KIND_TYPE_MAP.get(kind)
            if not want:
                return False
            return any(t in want for t in types)

        if kinds:
            normalized = [k.lower().strip() for k in kinds if isinstance(k, str)]
            normalized = [k for k in normalized if k in KIND_TYPE_MAP]
            if normalized:
                if kinds_mode == "all":
                    enriched_results = [p for p in enriched_results if all(has_kind(p, k) for k in normalized)]
                else:
                    enriched_results = [p for p in enriched_results if any(has_kind(p, k) for k in normalized)]

        # Sort
        reverse = True  # Default descending
        enriched_results.sort(key=lambda x: x.get(sort_by) or 0, reverse=reverse)

        total_count = len(enriched_results)
        response.headers["X-Total-Count"] = str(total_count)
        return enriched_results[:limit]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/vibes", response_model=List[Location])
def get_vibes(
    vibe_tag: Optional[str] = Query(None, description="Filter by vibe tag, e.g. Beloved_Dive, Consistent_Gem"),
    limit: int = Query(100, ge=1, le=500),
):
    try:
        db = get_supabase()
        q = db.table("locations").select("*")
        if vibe_tag:
            q = q.eq("vibe_tag", vibe_tag)
        resp = q.limit(limit).execute()
        # Enrich with computed scores
        enriched_results = [enrich_place(p) for p in resp.data]
        
        # Normalize each lens to percentiles so all top out ~9.5
        normalize_to_percentile(enriched_results, "quality_0_10")
        normalize_to_percentile(enriched_results, "character_0_10")
        normalize_to_percentile(enriched_results, "underrated_0_10")
        
        # Recalculate blended after normalization
        for place in enriched_results:
            place["blended_0_10"] = blended_0_10(place)
        
        return enriched_results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/custom", response_model=List[Location])
def get_locations_custom(
    response: Response,
    weights: str = Query(..., description="JSON object with signal weights, e.g. {\"food_drink_quality\": 0.8, \"divey_score\": 0.2}"),
    min_rating: float = Query(3.5, description="Minimum Google Rating"),
    min_reviews: int = Query(0, ge=0, description="Minimum Google review count"),
    limit: int = Query(120, ge=1, le=500, description="Max results returned"),
):
    """
    Custom lens: user provides weights for each signal.
    Computes a custom_score based on weighted average of the specified signals.
    Available signals: food_drink_quality, service_quality, value_score, divey_score,
    classic_institution, unpretentious, authenticity, would_recommend, memorable
    """
    import json as json_lib
    
    try:
        weight_dict = json_lib.loads(weights)
    except json_lib.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON in weights parameter")
    
    # Valid signal names and their DB column mappings
    SIGNAL_COLUMNS = {
        "food_drink_quality": "avg_food_drink_quality",
        "service_quality": "avg_service_quality",
        "value_score": "avg_value_score",
        "divey_score": "avg_divey_score",
        "classic_institution": "avg_classic_institution",
        "unpretentious": "avg_unpretentious",
        "authenticity": "avg_authenticity",
        "would_recommend": "avg_would_recommend",
        "memorable": "avg_memorable",
    }
    
    # Validate weights
    valid_weights = {}
    for signal, weight in weight_dict.items():
        if signal in SIGNAL_COLUMNS:
            try:
                valid_weights[signal] = float(weight)
            except (ValueError, TypeError):
                pass
    
    if not valid_weights:
        raise HTTPException(status_code=400, detail="No valid signal weights provided")
    
    try:
        db = get_supabase()
        query = db.table("locations").select("*").gte("rating", min_rating)
        sb_resp = query.execute()
        results = sb_resp.data
        
        # Enrich with standard scores first
        enriched_results = [enrich_place(place) for place in results]
        
        # Normalize each lens to percentiles so all top out ~9.5
        normalize_to_percentile(enriched_results, "quality_0_10")
        normalize_to_percentile(enriched_results, "character_0_10")
        normalize_to_percentile(enriched_results, "underrated_0_10")
        
        # Recalculate blended after normalization
        for place in enriched_results:
            place["blended_0_10"] = blended_0_10(place)
        
        # Filter by min reviews
        if min_reviews and min_reviews > 0:
            enriched_results = [
                p for p in enriched_results
                if int(p.get("user_ratings_total") or 0) >= int(min_reviews)
            ]
        
        # Compute custom score for each location
        for place in enriched_results:
            weighted_sum = 0.0
            total_weight = 0.0
            
            for signal, weight in valid_weights.items():
                col = SIGNAL_COLUMNS[signal]
                val = _safe_float(place.get(col), None)
                if val is not None and weight > 0:
                    weighted_sum += val * weight
                    total_weight += weight
            
            if total_weight > 0:
                # Scale to 0-10
                place["custom_score"] = round((weighted_sum / total_weight) * 10.0, 1)
            else:
                place["custom_score"] = 5.0  # Neutral default
        
        # Sort by custom score descending
        enriched_results.sort(key=lambda x: x.get("custom_score") or 0, reverse=True)
        
        total_count = len(enriched_results)
        response.headers["X-Total-Count"] = str(total_count)
        return enriched_results[:limit]
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/locations/{place_id}/reviews", response_model=List[ReviewOut])
def get_key_reviews(place_id: str, limit: int = Query(3, ge=1, le=8)):
    """
    Return a small set of representative reviews to help a user decide quickly:
    - most positive
    - most negative
    - most 'dive-positive' (if present)
    """
    try:
        db = get_supabase()
        resp = (
            db.table("reviews")
            .select("id,rating,review_text,author_name,openai_sentiment,openai_is_dive_positive")
            .eq("place_id", place_id)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return []

        # Filter out empty text
        rows = [r for r in rows if (r.get("review_text") or "").strip()]
        if not rows:
            return []

        # Sort candidates
        def sent(r):
            try:
                return float(r.get("openai_sentiment") or 0.0)
            except Exception:
                return 0.0

        most_pos = max(rows, key=sent)
        most_neg = min(rows, key=sent)
        dive_candidates = [r for r in rows if bool(r.get("openai_is_dive_positive"))]
        most_dive = max(dive_candidates, key=sent) if dive_candidates else None

        picked = []
        seen = set()
        for r in [most_pos, most_neg, most_dive]:
            if not r:
                continue
            rid = r.get("id")
            if rid and rid not in seen:
                picked.append(r)
                seen.add(rid)

        # If caller wants more than 3, fill with remaining highest-|sentiment| reviews
        if len(picked) < limit:
            remaining = [r for r in rows if r.get("id") not in seen]
            remaining.sort(key=lambda r: abs(sent(r)), reverse=True)
            for r in remaining:
                if len(picked) >= limit:
                    break
                picked.append(r)
                seen.add(r.get("id"))

        return picked[:limit]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
