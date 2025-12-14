import os
from outscraper import ApiClient
from supabase import create_client, Client
from dotenv import load_dotenv
from textblob import TextBlob

load_dotenv()

OUTSCRAPER_API_KEY = os.getenv("OUTSCRAPER_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

def get_supabase_client() -> Client:
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch_missing_reviews():
    supabase = get_supabase_client()
    client = ApiClient(api_key=OUTSCRAPER_API_KEY)
    
    # Target specifically Sam's No. 3
    target_place_id = "ChIJhw7HbNB4bIcR1RYprjjGutM"
    
    # Get details
    response = supabase.table("locations").select("name, address").eq("place_id", target_place_id).execute()
    if not response.data:
        print("Sam's No. 3 not found in DB")
        return
        
    loc = response.data[0]
    place_name = f"{loc['name']}, {loc['address']}"
    print(f"Fetching reviews for: {place_name}")
    
    try:
        results = client.google_maps_reviews([place_name], limit=50, language='en')
        reviews_data = []
        
        for place_result in results:
            for review in place_result.get("reviews_data", []):
                text = review.get("review_text", "")
                sentiment = 0.0
                if text:
                    sentiment = TextBlob(text).sentiment.polarity
                
                reviews_data.append({
                    "place_id": target_place_id,
                    "review_text": text,
                    "rating": review.get("rating"),
                    "author_name": review.get("author_title"),
                    "review_timestamp": review.get("review_datetime_utc"),
                    "sentiment_score": sentiment
                })
        
        if reviews_data:
            supabase.table("reviews").insert(reviews_data).execute()
            print(f"Saved {len(reviews_data)} reviews for Sam's No. 3")
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    fetch_missing_reviews()

