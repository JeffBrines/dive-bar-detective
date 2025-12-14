import os
import requests
from supabase import create_client, Client
from dotenv import load_dotenv
import time
import json

# Load environment variables
load_dotenv()

# Configuration
GOOGLE_MAPS_API_KEY = os.getenv("GOOGLE_MAPS_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Search Parameters
TARGET_CITY = "Denver, CO"
SEARCH_QUERIES = [
    f"Dive bars in {TARGET_CITY}",
    f"Hole in the wall restaurants in {TARGET_CITY}",
    f"Local favorite bars {TARGET_CITY}",
    f"Best cheap eats {TARGET_CITY}",
    f"Hidden gem restaurants {TARGET_CITY}"
]

def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise ValueError("Supabase credentials not found in environment variables.")
    return create_client(SUPABASE_URL, SUPABASE_KEY)

def search_places_new_api(query, api_key):
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": api_key,
        # Field mask for the new API
        "X-Goog-FieldMask": "places.id,places.displayName,places.formattedAddress,places.location,places.rating,places.userRatingCount,places.priceLevel,places.types,places.websiteUri,places.nationalPhoneNumber,nextPageToken"
    }
    
    all_places = []
    page_token = None
    
    # Limit to 3 pages per query to get a good sample (~60 results)
    for _ in range(3):
        payload = {
            "textQuery": query,
            "pageSize": 20
        }
        if page_token:
            payload["pageToken"] = page_token
            
        try:
            response = requests.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()
            
            places = data.get("places", [])
            all_places.extend(places)
            
            page_token = data.get("nextPageToken")
            if not page_token:
                break
                
            time.sleep(2) # Be nice to the API
            
        except Exception as e:
            print(f"Error searching '{query}': {e}")
            break
            
    return all_places

def map_price_level(price_enum):
    """Maps Google Places New API priceLevel enum to integer 0-4"""
    mapping = {
        "PRICE_LEVEL_FREE": 0,
        "PRICE_LEVEL_INEXPENSIVE": 1,
        "PRICE_LEVEL_MODERATE": 2,
        "PRICE_LEVEL_EXPENSIVE": 3,
        "PRICE_LEVEL_VERY_EXPENSIVE": 4
    }
    return mapping.get(price_enum, None)

def transform_place(place):
    """Transform New Places API format to Supabase schema"""
    return {
        "place_id": place.get("id"),
        "name": place.get("displayName", {}).get("text"),
        "address": place.get("formattedAddress"),
        "lat": place.get("location", {}).get("latitude"),
        "lng": place.get("location", {}).get("longitude"),
        "rating": place.get("rating"),
        "user_ratings_total": place.get("userRatingCount"),
        "price_level": map_price_level(place.get("priceLevel")),
        "types": place.get("types", []),
        "formatted_phone_number": place.get("nationalPhoneNumber"),
        "website": place.get("websiteUri")
    }

def main():
    print("Dive Bar Detective - Data Collector (New Places API)")
    
    if not GOOGLE_MAPS_API_KEY:
        print("Error: GOOGLE_MAPS_API_KEY not found.")
        return

    try:
        supabase = get_supabase_client()
        
        for query in SEARCH_QUERIES:
            print(f"Searching for: {query}...")
            places = search_places_new_api(query, GOOGLE_MAPS_API_KEY)
            
            batch_data = []
            for p in places:
                batch_data.append(transform_place(p))
            
            if batch_data:
                # Upsert to Supabase
                # We assume place_id collision is fine (upsert updates existing)
                result = supabase.table("locations").upsert(batch_data).execute()
                print(f"  - Upserted {len(batch_data)} places.")
            else:
                print("  - No results found.")
            
        print("\nCollection complete!")
        
    except Exception as e:
        print(f"Fatal error: {e}")

if __name__ == "__main__":
    main()
