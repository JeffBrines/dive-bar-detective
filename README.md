# Dive Bar Detective 🕵️

By Jeff Brines.

A data-driven "Sommelier for Dive Bars" that helps you find off-the-beaten-path spots using NLP, ML, and custom scoring lenses. Stop trusting inflated Google ratings — find places with real character.

**Live Demo**: [GitHub Repository](https://github.com/JeffBrines/dive-bar-detective)

## What It Does

- **Analyzes 4,260 reviews** using GPT-5-nano to extract 9 quality/vibe signals
- **Scores places on 4 lenses**: Quality, Character, Underrated, Blended
- **Custom lens builder**: Weight the 9 signals yourself to create your own scoring formula
- **Vibe Map**: Interactive scatter plot showing Quality vs Character — find hidden gems in the top-right!
- **ML-ready features**: UMAP visualization, auto-tagging, anomaly detection

## Quick Start

### 1. Setup

```bash
# Clone and setup environment
git clone https://github.com/JeffBrines/dive-bar-detective.git
cd dive-bar-detective
cp env.example .env  # Add your API keys
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Required API keys in `.env`:
- `SUPABASE_URL` / `SUPABASE_KEY` — Database
- `OPENAI_API_KEY` — NLP analysis (if re-running)
- `GOOGLE_MAPS_API_KEY` — Place data (optional, for new data collection)

### 2. Run the App

```bash
# Terminal 1: Start API
source venv/bin/activate
uvicorn src.api:app --port 8000

# Terminal 2: Start frontend
python3 -m http.server 5500
```

Open: http://localhost:5500

---

## Deployment to Production

This app is configured for easy deployment to [Render](https://render.com) with automatic CI/CD.

### Prerequisites

1. **GitHub Account**: Push your code to a GitHub repository
2. **Render Account**: Sign up at [render.com](https://render.com) (free tier available)
3. **API Keys Ready**: Have your production API keys ready (Supabase, OpenAI, etc.)

### Deploy to Render

#### Option 1: One-Click Deploy (Recommended)

1. **Push to GitHub**:
   ```bash
   git add .
   git commit -m "Ready for deployment"
   git push origin main
   ```

2. **Create Render Account**: Sign up at render.com and connect your GitHub account

3. **Deploy via Blueprint**:
   - Click "New" → "Blueprint"
   - Select your GitHub repository
   - Render will automatically read `render.yaml` and create:
     - **Single Web Service**: FastAPI backend serving static frontend at `https://dive-bar-detective.onrender.com`

4. **Set Environment Variables** in Render Dashboard:
   
   Navigate to your backend service settings and add:
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-anon-key
   OPENAI_API_KEY=sk-your-openai-key
   GOOGLE_MAPS_API_KEY=your-google-maps-key
   OUTSCRAPER_API_KEY=your-outscraper-key (optional)
   ```
   
   See `env.production.example` for the complete list.

5. **Deploy**: Render will automatically build and deploy both services (takes 3-5 minutes)

#### Option 2: Manual Service Creation

If you prefer manual setup:

1. **Create Web Service**:
   - New → Web Service
   - Connect repository
   - Name: `dive-bar-detective`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn src.api:app --workers 2 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT --timeout 120`
   - Add environment variables (see step 4 above)

### Automatic Deployments

Once connected to GitHub, Render automatically deploys when you push to your main branch:

```bash
git add .
git commit -m "Update feature"
git push origin main
# Render deploys automatically in 2-5 minutes
```

### Production URL

After deployment, your app will be available at:
- **Single URL**: `https://dive-bar-detective.onrender.com`
- API endpoints at same URL (e.g., `/locations`, `/vibes`)

Much simpler - one service, one URL, no CORS complexity!

### Cost

- **Free Tier**: Backend + Frontend = $0/month
  - Backend sleeps after 15 min inactivity (30s cold start)
  - 750 hours/month (enough for moderate usage)
  - Unlimited static site hosting

- **Paid Tier**: $7/month for backend
  - No sleep/downtime
  - Better performance
  - More resources

### Monitoring

Monitor your deployment in the Render Dashboard:
- View real-time logs
- Check deployment status
- Monitor resource usage
- Set up custom domains

### Troubleshooting

**Backend won't start?**
- Check environment variables are set correctly
- Review logs in Render Dashboard
- Verify `requirements.txt` has all dependencies

**Frontend can't connect to API?**
- Check CORS settings in `src/api.py`
- Verify backend is running (visit `/` endpoint)
- Check browser console for errors

**Cold starts too slow?**
- Upgrade to paid tier ($7/month) for always-on backend
- Or use a service like UptimeRobot to ping your API every 10 minutes

### Custom Domain (Optional)

To use your own domain:
1. Add CNAME record pointing to Render URL
2. Configure custom domain in Render Dashboard
3. Render provides free SSL certificates

---

## Scoring Lenses (0-10 scale)

| Lens | What It Measures | Formula |
|------|------------------|---------|
| **Quality** | Is it actually good? | 35% food + 30% recommend + 15% service + 10% value + 10% memorable |
| **Character** | Does it have soul? | 30% authenticity + 25% classic + 20% unpretentious + 15% divey + 10% memorable |
| **Underrated** | Better than Google suggests? | 40% recommend-gap + 30% sentiment-gap + 30% discovery factor |
| **Blended** | Best overall | 40% Quality + 35% Character + 25% Underrated |
| **Custom** | Your own formula | User-defined weights for all 9 signals |

---

## Vibe Map 🎯

The **Vibe Map** plots every place on a Quality (X) vs Character (Y) scatter chart:

| Quadrant | Meaning |
|----------|---------|
| 🌟 **Top-Right** | Best Finds — above median on both axes |
| 🍺 **Top-Left** | Character — authentic vibe, rougher quality |
| ✨ **Bottom-Right** | Quality — good food/service, less character |
| 📍 **Bottom-Left** | Average — below median on both |

**Controls:**
- Scroll to zoom in/out
- Shift+drag to pan
- Click any dot to see details
- Reset Zoom button to restore view

**Features:**
- Auto-scales axes to data bounds (no wasted space)
- Dashed lines at median (splits places in half)
- Slight jitter to spread overlapping points
- Rank-based bubble sizing for visual variance

---

## NLP Signals (extracted per review)

Each review is analyzed by GPT-5-nano to extract these signals (0-1 scale):

| Signal | Description |
|--------|-------------|
| `food_drink_quality` | How good is the food/drinks? |
| `service_quality` | Staff friendliness, attentiveness |
| `value_score` | Bang for buck |
| `divey_score` | Gritty dive bar energy |
| `classic_institution` | Neighborhood staple, been there forever |
| `unpretentious` | Laid-back, no pretense vibe |
| `authenticity` | Genuine character, not corporate |
| `would_recommend` | Would reviewer recommend? |
| `memorable` | Unique, stands out |

These are aggregated per location and used to compute the lens scores.

---

## ML Features (Ready to Run)

| Feature | Script | Description |
|---------|--------|-------------|
| **UMAP Visualization** | `src/umap_viz.py` | Reduce 9 signals to 2D for "vibe space" clustering |
| **Auto-Tagging** | `src/topic_modeling.py` | Extract topic labels from reviews (e.g., "late-night", "patio") |
| **Anomaly Detection** | `src/anomaly_detection.py` | Find "truly unique" places using Isolation Forest |
| **Vibe Clustering** | `src/vibe_clustering.py` | KMeans clustering for vibe_tag labels |

---

## Data Pipeline

```
1. Collect places     → src/collect_data.py (Google Places API)
2. Fetch reviews      → src/fetch_reviews.py (Outscraper)
3. NLP analysis       → src/hybrid_analysis.py (GPT-5-nano) ✅ COMPLETE
4. Feature eng        → src/feature_engineering.py (aggregate signals)
5. ML enrichment      → src/umap_viz.py, topic_modeling.py, anomaly_detection.py
```

### Run the full pipeline:

```bash
# NLP analysis (already complete for 4,260 reviews)
caffeinate -i python src/hybrid_analysis.py

# Aggregate signals to locations
python src/feature_engineering.py

# Generate ML features
python src/umap_viz.py
python src/topic_modeling.py --simple
python src/anomaly_detection.py
```

---

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /locations` | List all locations with lens scores |
| `GET /locations?sort_by=quality_0_10` | Sort by any lens |
| `GET /locations/custom?weights={...}` | Custom lens with user weights |
| `GET /locations/{place_id}/reviews` | Key reviews for a place |
| `GET /vibes?vibe_tag=Beloved_Dive` | Filter by vibe cluster |

---

## Frontend Features

- **Map + List split view** with Leaflet.js
- **Vibe Map**: Quality vs Character scatter plot with zoom/pan
- **Lens selector**: Blended, Quality, Character, Underrated, Custom
- **Custom Lens Builder**: 9 sliders to weight signals
- **Minimum score filter**: Hide low-scoring places
- **Type filter**: Bar, Restaurant, Both, All
- **Badges**: Underrated, Unique, Low Data, Auto-tags
- **Details panel**: Quick stats, key reviews, links

---

## Tech Stack

- **Backend**: FastAPI, Python 3.14
- **Database**: Supabase (PostgreSQL + PostGIS)
- **NLP**: OpenAI GPT-5-nano
- **ML**: scikit-learn, UMAP, BERTopic
- **Frontend**: Vanilla HTML/JS, Leaflet.js, Chart.js

---

## Dataset

- **251 locations** in Denver metro area
- **4,260 reviews** analyzed with GPT-5-nano
- **9 signals per review** → aggregated to location scores
- **4 pre-built lenses** + custom lens builder

---

## License

MIT — Built for fun and learning.
