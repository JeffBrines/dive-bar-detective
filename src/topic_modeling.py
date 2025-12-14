"""
BERTopic Auto-Tagging - Extract topic labels from review text for each location.
Creates auto-generated tags like "late-night", "patio", "craft-beer".
"""
import os
import json
from collections import Counter
from typing import List, Dict
import pandas as pd
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# Configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)


def fetch_reviews_by_location() -> Dict[str, List[str]]:
    """Fetch all reviews grouped by place_id."""
    supabase = get_supabase_client()
    
    reviews_by_place = {}
    offset = 0
    batch_size = 1000
    
    while True:
        resp = supabase.table("reviews").select("place_id, review_text").range(offset, offset + batch_size - 1).execute()
        batch = resp.data or []
        if not batch:
            break
        
        for row in batch:
            place_id = row.get("place_id")
            text = (row.get("review_text") or "").strip()
            if place_id and text:
                if place_id not in reviews_by_place:
                    reviews_by_place[place_id] = []
                reviews_by_place[place_id].append(text)
        
        offset += batch_size
        print(f"  Fetched {offset} reviews...")
    
    print(f"Total: {sum(len(v) for v in reviews_by_place.values())} reviews across {len(reviews_by_place)} locations")
    return reviews_by_place


def extract_topics_bertopic(reviews_by_place: Dict[str, List[str]], top_n_topics: int = 5) -> Dict[str, List[str]]:
    """
    Run BERTopic on all reviews, then map topics back to locations.
    Returns dict of place_id -> list of topic labels.
    """
    try:
        from bertopic import BERTopic
    except ImportError:
        print("bertopic not installed. Run: pip install bertopic")
        return {}
    
    # Prepare documents and track which location each came from
    all_docs = []
    doc_to_place = []
    
    for place_id, reviews in reviews_by_place.items():
        for text in reviews:
            all_docs.append(text)
            doc_to_place.append(place_id)
    
    print(f"Training BERTopic on {len(all_docs)} documents...")
    
    # Fit BERTopic
    topic_model = BERTopic(
        language="english",
        calculate_probabilities=False,
        verbose=True,
        min_topic_size=10,  # Smaller clusters for more granular topics
    )
    
    topics, _ = topic_model.fit_transform(all_docs)
    
    # Get topic info
    topic_info = topic_model.get_topic_info()
    print(f"\nFound {len(topic_info) - 1} topics (excluding outlier topic -1)")
    
    # Map topics to labels (use top keywords)
    topic_labels = {}
    for idx, row in topic_info.iterrows():
        topic_id = row['Topic']
        if topic_id == -1:
            continue  # Skip outlier topic
        # Get top 2 keywords for label
        topic_words = topic_model.get_topic(topic_id)
        if topic_words:
            label = "-".join([w[0] for w in topic_words[:2]])
            topic_labels[topic_id] = label
    
    print(f"Topic labels: {topic_labels}")
    
    # Count topics per location
    location_topics = {}
    for doc_idx, topic_id in enumerate(topics):
        if topic_id == -1:
            continue
        place_id = doc_to_place[doc_idx]
        if place_id not in location_topics:
            location_topics[place_id] = Counter()
        location_topics[place_id][topic_id] += 1
    
    # Get top N topics per location
    result = {}
    for place_id, topic_counts in location_topics.items():
        top_topics = topic_counts.most_common(top_n_topics)
        labels = [topic_labels.get(t[0], f"topic-{t[0]}") for t in top_topics if t[0] in topic_labels]
        result[place_id] = labels[:top_n_topics]
    
    return result


def extract_topics_simple(reviews_by_place: Dict[str, List[str]], top_n: int = 5) -> Dict[str, List[str]]:
    """
    Simple keyword-based topic extraction (fallback if BERTopic not available).
    Uses predefined topic keywords.
    """
    # Predefined topic patterns
    TOPIC_PATTERNS = {
        "late-night": ["late night", "midnight", "2am", "3am", "open late", "after hours"],
        "patio": ["patio", "outdoor", "outside seating", "rooftop", "deck"],
        "craft-beer": ["craft beer", "microbrew", "ipa", "local beer", "tap list", "beer selection"],
        "cocktails": ["cocktail", "mixology", "martini", "old fashioned", "manhattan"],
        "dive-bar": ["dive", "hole in the wall", "cash only", "sticky", "no frills"],
        "sports": ["sports bar", "game", "big screen", "watch the game", "nfl", "nba"],
        "live-music": ["live music", "band", "karaoke", "dj", "open mic"],
        "brunch": ["brunch", "mimosa", "bloody mary", "eggs", "breakfast"],
        "happy-hour": ["happy hour", "specials", "half off", "drink deals"],
        "local-favorite": ["local", "neighborhood", "regulars", "hidden gem", "best kept secret"],
        "cheap-drinks": ["cheap", "affordable", "well drinks", "pbr", "budget"],
        "food-focused": ["food", "menu", "burger", "wings", "kitchen", "chef"],
        "date-spot": ["date", "romantic", "intimate", "cozy", "ambiance"],
        "group-friendly": ["group", "party", "friends", "birthday", "celebration"],
        "dog-friendly": ["dog", "pet friendly", "pup", "bring your dog"],
    }
    
    result = {}
    
    for place_id, reviews in reviews_by_place.items():
        combined = " ".join(reviews).lower()
        topic_scores = {}
        
        for topic, patterns in TOPIC_PATTERNS.items():
            score = sum(combined.count(p.lower()) for p in patterns)
            if score > 0:
                topic_scores[topic] = score
        
        # Get top N topics
        sorted_topics = sorted(topic_scores.items(), key=lambda x: x[1], reverse=True)
        result[place_id] = [t[0] for t in sorted_topics[:top_n]]
    
    return result


def save_tags_to_db(tags_by_place: Dict[str, List[str]], batch_size: int = 50):
    """Save auto-tags to locations table."""
    supabase = get_supabase_client()
    
    items = list(tags_by_place.items())
    total = len(items)
    
    for i in range(0, total, batch_size):
        batch = items[i:i+batch_size]
        for place_id, tags in batch:
            supabase.table("locations").update({
                "auto_tags": tags
            }).eq("place_id", place_id).execute()
        
        print(f"Updated {min(i+batch_size, total)}/{total} locations")
    
    print("Done saving auto-tags!")


def main(use_bertopic: bool = True):
    print("=== Topic Modeling / Auto-Tagging ===\n")
    
    # Fetch reviews
    print("Fetching reviews...")
    reviews_by_place = fetch_reviews_by_location()
    
    if not reviews_by_place:
        print("No reviews found!")
        return
    
    # Extract topics
    if use_bertopic:
        try:
            tags_by_place = extract_topics_bertopic(reviews_by_place)
        except Exception as e:
            print(f"BERTopic failed: {e}")
            print("Falling back to simple keyword extraction...")
            tags_by_place = extract_topics_simple(reviews_by_place)
    else:
        tags_by_place = extract_topics_simple(reviews_by_place)
    
    if not tags_by_place:
        print("No topics extracted!")
        return
    
    # Show sample
    print("\nSample auto-tags:")
    for place_id, tags in list(tags_by_place.items())[:5]:
        print(f"  {place_id[:20]}...: {tags}")
    
    # Save to database
    print("\nSaving to database...")
    save_tags_to_db(tags_by_place)
    
    print("\n✅ Auto-tagging complete!")


if __name__ == "__main__":
    import sys
    use_bertopic = "--simple" not in sys.argv
    main(use_bertopic=use_bertopic)
