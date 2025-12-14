import os
from outscraper import ApiClient
from supabase import create_client, Client
from dotenv import load_dotenv
from textblob import TextBlob
import time

load_dotenv()

# Configuration
OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not OUTSCRAPER_API_KEY:
    print("Warning: OUTSCRAPER_API_KEY not found. Please set it in .env")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_and_process_reviews():
    supabase = get_supabase_client()
    
    # Get locations that don't have detailed reviews yet (or just top rated ones to save credits)
    # Fetch ALL locations for full scrape
    response = supabase.table("locations")\
        .select("place_id, name, address")\
        .execute()
    
    locations = response.data
    
    if not locations:
        print("No locations found to process.")
        return

    print(f"Processing {len(locations)} locations for deep review extraction...")
    
    client = ApiClient(api_key=OUTSCRAPER_API_KEY)

    for loc in locations:
        place_name = f"{loc['name']}, {loc['address']}"
        print(f"Fetching reviews for: {place_name}")
        
        try:
            # Outscraper can search by query directly
            # We limit to 50 reviews per place for the prototype to save credits
            results = client.google_maps_reviews(
                [place_name], 
                limit=50, 
                language='en'
            )
            
            reviews_data = []
            
            for place_result in results:
                for review in place_result.get("reviews_data", []):
                    
                    # Calculate Sentiment
                    text = review.get("review_text", "")
                    sentiment = 0.0
                    if text:
                        sentiment = TextBlob(text).sentiment.polarity
                    
                    reviews_data.append({
                        "place_id": loc["place_id"],
                        "review_text": text,
                        "rating": review.get("rating"),
                        "author_name": review.get("author_title"),
                        "review_timestamp": review.get("review_datetime_utc"), # Format might need adjustment
                        "sentiment_score": sentiment
                    })
            
            if reviews_data:
                # Batch insert reviews
                supabase.table("reviews").insert(reviews_data).execute()
                print(f"  - Saved {len(reviews_data)} reviews.")
            else:
                print("  - No reviews found via Outscraper.")
                
        except Exception as e:
            print(f"Error processing {place_name}: {e}")

if __name__ == "__main__":
    if not OUTSCRAPER_API_KEY:
        print("Error: Cannot run without OUTSCRAPER_API_KEY")
    else:
        fetch_and_process_reviews()

