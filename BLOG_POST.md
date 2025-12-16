# Building a "Sommelier for Dive Bars": How I Used NLP and ML to Find Denver's Hidden Gems

**By Jeff Brines**

*Stop trusting inflated Google ratings. Let's find places with real character.*

---

## The Problem: Google Ratings Are Broken

You know the feeling. You're looking for a great dive bar—somewhere with character, authentic vibes, maybe a little rough around the edges but with surprisingly good food. You open Google Maps, see a place with 4.2 stars, and think "eh, probably not worth it."

**You just missed a hidden gem.**

Google's star ratings are a blunt instrument. They don't tell you *why* a place is rated that way. Is it 4.2 stars because the bathroom is sketchy but the burgers are incredible? Or because it's genuinely mediocre? You have no idea.

I wanted something better. A way to find places that are **underrated**, **authentic**, and have **real character**—even if their Google rating doesn't reflect it.

So I built **Dive Bar Detective** 🕵️.

---

## What It Does: Multi-Dimensional Scoring for Bars

Dive Bar Detective analyzes **4,260 reviews** across **251 locations** in Denver using GPT-5-nano to extract 9 quality and vibe signals from each review. Then it scores every place on 4 different "lenses":

| Lens | What It Measures |
|------|------------------|
| **Quality** | Is it actually good? (food, service, value) |
| **Character** | Does it have soul? (authenticity, divey-ness, classic vibes) |
| **Underrated** | Better than Google suggests? (recommendation gap, sentiment gap) |
| **Blended** | Best overall (weighted combo of all three) |

Plus, you can build your own **Custom Lens** by adjusting 9 sliders to weight the signals however you want.

The result? A ranked list of places sorted by *what you actually care about*, not just a single star rating.

---

## The Tech Stack: NLP Meets Traditional ML

### 1. Data Collection
I started with the Google Places API to find 251 bars and restaurants in Denver, then used Outscraper to pull their reviews. Total haul: **4,260 reviews** with full text.

### 2. NLP Analysis with GPT-5-nano
Here's where it gets interesting. I fed every review through OpenAI's `gpt-5-nano` model to extract **9 signals** (0-1 scale):

- **Quality signals**: `food_drink_quality`, `service_quality`, `value_score`
- **Character signals**: `divey_score`, `classic_institution`, `unpretentious`, `authenticity`
- **Sentiment signals**: `would_recommend`, `memorable`

Example prompt:
```
Analyze this review and extract quality/vibe signals on a 0-1 scale:
- food_drink_quality: How good is the food/drinks?
- divey_score: Gritty dive bar energy?
- authenticity: Genuine character, not corporate?
...
```

The model returns structured JSON for each review. I aggregate these per location to get average scores.

### 3. Scoring Lenses
Each lens is a weighted formula. For example:

**Quality Lens** = 35% food + 30% recommend + 15% service + 10% value + 10% memorable

**Character Lens** = 30% authenticity + 25% classic + 20% unpretentious + 15% divey + 10% memorable

**Underrated Lens** = 40% (recommend - Google rating) + 30% (sentiment - Google rating) + 30% discovery factor

All scores are normalized to a **0-10 scale** for easy comparison.

### 4. The Vibe Map
The coolest feature: a **Quality vs Character scatter plot** that shows every location's position in "vibe space."

- **Top-right quadrant** = Best Finds (high quality + high character)
- **Top-left** = Character spots (authentic but rough)
- **Bottom-right** = Quality spots (good but generic)
- **Bottom-left** = Average (below median on both)

You can zoom, pan, and click any dot to see details. It's like a treasure map for dive bars.

---

## The Results: Finding Hidden Gems

Here's what makes this useful:

### Example 1: The Underrated Gem
**Adrift Tiki Bar** has a 4.3 Google rating (decent, not amazing). But when you look at the NLP signals:
- `would_recommend`: 0.92 (people LOVE it)
- `authenticity`: 0.88 (genuine tiki vibes)
- `memorable`: 0.85 (stands out)

**Underrated Score**: 8.7/10 🎯

The reviews say things like "hidden gem," "best tiki bar in Denver," "don't let the exterior fool you." Google's 4.3 doesn't capture that.

### Example 2: The Character Spot
**Sancho's Broken Arrow** has a 4.1 rating. Sounds mediocre, right? But:
- `divey_score`: 0.91 (gritty dive energy)
- `classic_institution`: 0.87 (neighborhood staple)
- `unpretentious`: 0.93 (zero pretense)

**Character Score**: 9.1/10 🍺

It's exactly what you want in a dive bar, but Google's rating makes it look average.

---

## The ML Layer: Auto-Tagging and Anomaly Detection

The NLP signals are just the beginning. I built a few ML features on top:

### 1. UMAP Visualization
Reduces the 9 signals to 2D coordinates for clustering. This lets you visualize "vibe neighborhoods"—groups of places with similar characteristics.

### 2. Auto-Tagging with BERTopic
Extracts topic labels from review text (e.g., "late-night spot," "patio vibes," "live music"). These show up as badges in the UI.

### 3. Anomaly Detection with Isolation Forest
Finds places that are statistically unique—outliers in the 9-signal space. These are the truly one-of-a-kind spots.

All of this is **ready to run** with simple Python scripts:
```bash
python src/umap_viz.py
python src/topic_modeling.py --simple
python src/anomaly_detection.py
```

---

## The Frontend: Interactive and Fast

The UI is built with vanilla HTML/JS (no framework bloat) and includes:

- **Split view**: Map + List side-by-side
- **Vibe Map**: Interactive scatter plot with zoom/pan
- **Lens selector**: Switch between Blended, Quality, Character, Underrated, Custom
- **Custom Lens Builder**: 9 sliders to weight signals in real-time
- **Filters**: Minimum score, place type (bar/restaurant/both)
- **Badges**: Underrated, Unique, Low Data, Auto-tags
- **Details panel**: Quick stats, key reviews, Google Maps link

Everything updates instantly as you adjust filters. No page reloads.

---

## The Architecture: FastAPI + Supabase

**Backend**: FastAPI with Python 3.14
- Endpoints for locations, reviews, custom lenses, vibe filtering
- Lens calculations happen server-side for consistency
- CORS configured for production deployment

**Database**: Supabase (PostgreSQL + PostGIS)
- `locations` table: 251 rows with aggregated signals + ML fields
- `reviews` table: 4,260 rows with full text + per-review NLP enrichments

**Deployment**: Render.com with automatic CI/CD
- Push to GitHub → auto-deploy in 2-5 minutes
- Free tier available (backend sleeps after 15min inactivity)
- Production URLs: frontend + backend on Render

---

## Lessons Learned

### 1. GPT-5-nano Is Perfect for Structured Extraction
I initially tried regex and keyword matching to extract signals. It was a mess. GPT-5-nano is fast (~6 reviews/min), cheap, and incredibly consistent at returning structured JSON.

### 2. Multi-Dimensional Scoring > Single Rating
A single star rating collapses too much information. By separating Quality, Character, and Underrated, you can find places that excel in specific ways—even if their overall rating is mediocre.

### 3. The Vibe Map Is the Killer Feature
People love the scatter plot. It's intuitive, interactive, and makes patterns obvious at a glance. The top-right quadrant is where the magic happens.

### 4. Custom Lenses Are Surprisingly Useful
Different people care about different things. Some want the highest quality. Others want maximum dive bar energy. The custom lens builder lets everyone create their own "perfect" ranking.

---

## What's Next

I'm planning to add:
- **More cities**: Expand beyond Denver
- **Collaborative filtering**: "People who liked X also liked Y"
- **Time-based analysis**: How do places change over time?
- **Mobile app**: Native iOS/Android with offline support

But for now, it's live and ready to use. Check it out:

🔗 **Live Demo**: [GitHub Repository](https://github.com/JeffBrines/dive-bar-detective)

---

## Try It Yourself

Want to build something similar? The entire codebase is open-source (MIT license). Here's how to get started:

```bash
# Clone the repo
git clone https://github.com/JeffBrines/dive-bar-detective.git
cd dive-bar-detective

# Setup environment
cp env.example .env  # Add your API keys
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Run the app
uvicorn src.api:app --port 8000  # Terminal 1
python3 -m http.server 5500      # Terminal 2

# Open http://localhost:5500
```

You'll need:
- Supabase account (free tier works)
- OpenAI API key (for NLP analysis)
- Google Maps API key (optional, for new data collection)

---

## Final Thoughts

This project started as a weekend experiment and turned into a full-fledged app. It's been a great excuse to learn FastAPI, play with modern NLP models, and build something genuinely useful.

The best part? I've actually discovered amazing places I never would have found otherwise. Turns out, the best dive bars often have mediocre Google ratings. You just need the right lens to see them.

**Stop trusting star ratings. Start finding character.**

---

*Questions? Want to chat about NLP, ML, or dive bars? Find me on GitHub: [@JeffBrines](https://github.com/JeffBrines)*

---

## Tech Specs (for the nerds)

- **Language**: Python 3.14
- **Backend**: FastAPI, Uvicorn, Gunicorn
- **Database**: Supabase (PostgreSQL + PostGIS)
- **NLP**: OpenAI GPT-5-nano
- **ML**: scikit-learn, UMAP, BERTopic, Isolation Forest
- **Frontend**: Vanilla JS, Leaflet.js, Chart.js
- **Deployment**: Render.com (free tier)
- **Dataset**: 251 locations, 4,260 reviews, 9 signals per review

Total NLP processing time: ~10 hours (caffeinated)
Total cost: ~$15 in OpenAI API credits

Worth it? Absolutely.




