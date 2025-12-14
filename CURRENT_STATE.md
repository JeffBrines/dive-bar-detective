# Dive Bar Detective - State of the App (December 2025)

## 🎯 Mission
A data-driven "Sommelier for Dive Bars" that finds off-the-beaten-path spots using NLP, ML, and custom scoring lenses.

---

## 🆕 Latest Update (Dec 15, 2025)

### Phase 1: NLP Re-run (IN PROGRESS)
- Reset all 4,260 reviews for consistent `gpt-5-nano` processing
- Running in background with `caffeinate` (~3 hours total)
- Extracts 9 rich signals per review

### Phase 2: Reworked Lenses ✅
| Lens | Formula | Purpose |
|------|---------|---------|
| **Quality** | 35% food + 30% recommend + 15% service + 10% value + 10% memorable | Is it good? |
| **Character** | 30% authenticity + 25% classic + 20% unpretentious + 15% divey + 10% memorable | Has soul? |
| **Underrated** | 40% recommend-gap + 30% sentiment-gap + 30% discovery factor | Hidden gem? |
| **Blended** | 40% Quality + 35% Character + 25% Underrated | Best overall |

### Phase 3: Custom Lens Builder ✅
- API: `GET /locations/custom?weights={"food_drink_quality":0.8,...}`
- Frontend: 9 signal sliders to build your own scoring formula

### Phase 4: ML Features ✅
| Feature | Script | Database Column |
|---------|--------|-----------------|
| UMAP Viz | `src/umap_viz.py` | `umap_x`, `umap_y` |
| Auto-Tags | `src/topic_modeling.py` | `auto_tags` (jsonb) |
| Anomaly Detection | `src/anomaly_detection.py` | `anomaly_score` |

### Frontend Updates ✅
- **View Toggle**: Switch between "List" and "Vibe Map" views
- **Vibe Map**: Chart.js scatter plot showing places in 2D vibe space
- **Lens Dropdown**: Blended, Quality, Character, Underrated, Custom
- **Custom Lens Builder**: 9 sliders (Food, Service, Value, Divey, Classic, etc.)
- **Badges**: Auto-tags, ✨ Unique, 📈 Underrated, ⚠️ Low Data
- **Updated About Modal**: Explains all lenses and badges

---

## 🏗️ Architecture

### Data Layer
- **Database**: Supabase (PostgreSQL + PostGIS)
- **Tables**:
  - `locations` (251 rows): Place metadata + 9 avg signals + ML fields
  - `reviews` (4,260 rows): Full text + per-review NLP enrichments

### NLP Signals (0-1 scale per review)
| Signal | Description |
|--------|-------------|
| food_drink_quality | How good is the food/drinks? |
| service_quality | Staff friendliness |
| value_score | Bang for buck |
| divey_score | Gritty dive bar energy |
| classic_institution | Neighborhood staple |
| unpretentious | Laid-back vibe |
| authenticity | Genuine character |
| would_recommend | Would recommend? |
| memorable | Unique, stands out |

### ML Models
| Model | Purpose |
|-------|---------|
| Vibe Clustering (KMeans) | Groups by sentiment/variance → vibe_tag |
| UMAP | 2D scatter plot visualization |
| BERTopic | Auto-tagging from review text |
| Isolation Forest | Anomaly detection for unique spots |

---

## 📁 Key Files

### Backend (`src/`)
| File | Purpose |
|------|---------|
| `api.py` | FastAPI with lens calculations, custom endpoint |
| `hybrid_analysis.py` | NLP processing with gpt-5-nano |
| `feature_engineering.py` | Aggregate signals to locations |
| `umap_viz.py` | UMAP dimensionality reduction |
| `topic_modeling.py` | BERTopic / keyword auto-tagging |
| `anomaly_detection.py` | Isolation Forest unique detection |

### Frontend
| File | Features |
|------|----------|
| `index.html` | Full UI: map, list, vibe map, custom lens builder |

---

## 🚀 Next Steps (After NLP Completes)

```bash
# 1. Update location aggregates
python src/feature_engineering.py

# 2. Generate UMAP coordinates for Vibe Map
python src/umap_viz.py

# 3. Auto-tag locations
python src/topic_modeling.py --simple

# 4. Detect unique places
python src/anomaly_detection.py
```

---

## 📊 Current Status

| Item | Status |
|------|--------|
| NLP Processing | ~40/4,260 reviews (~3 hours remaining) |
| API | Running on localhost:8000 |
| Frontend | Running on localhost:5500 |
| Lenses | ✅ All working (Blended, Quality, Character, Underrated, Custom) |
| View Toggle | ✅ List / Vibe Map |
| UMAP Data | ⏳ Waiting for NLP + umap_viz.py |
| Auto-Tags | ⏳ Waiting for topic_modeling.py |
| Anomaly Scores | ⏳ Waiting for anomaly_detection.py |
