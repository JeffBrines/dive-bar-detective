# Dive Bar Detective - State of the App (December 2025)

## 🎯 Mission
A data-driven "Sommelier for Dive Bars" that finds off-the-beaten-path spots using NLP, ML, and custom scoring lenses.

---

## 🆕 Latest Update (Dec 14, 2025)

### ✅ NLP Processing Complete
- **All 4,260 reviews** analyzed with `gpt-5-nano`
- Extracts 9 rich signals per review (food quality, service, value, divey-ness, authenticity, etc.)
- Consistent scoring across entire dataset

### ✅ Scoring Lenses
| Lens | Formula | Purpose |
|------|---------|---------|
| **Quality** | 35% food + 30% recommend + 15% service + 10% value + 10% memorable | Is it good? |
| **Character** | 30% authenticity + 25% classic + 20% unpretentious + 15% divey + 10% memorable | Has soul? |
| **Underrated** | 40% recommend-gap + 30% sentiment-gap + 30% discovery factor | Hidden gem? |
| **Blended** | 40% Quality + 35% Character + 25% Underrated | Best overall |
| **Custom** | User-defined weights | Build your own lens |

### ✅ Frontend Features
- **View Toggle**: Switch between "List" and "Vibe Map" views
- **Vibe Map**: Interactive Quality vs Character scatter plot
  - Scroll to zoom, shift+drag to pan
  - Dynamic quadrants at median (splits places in half)
  - Color-coded by lens score, sized by rank
- **Custom Lens Builder**: 9 sliders to weight signals
- **Lens Dropdown**: Blended, Quality, Character, Underrated, Custom
- **Badges**: Underrated, Unique, Low Data, Auto-tags (ready for ML)

### ⏳ ML Features (Ready to Run)
| Feature | Script | Status |
|---------|--------|--------|
| UMAP Viz | `src/umap_viz.py` | ⏳ Ready to generate 2D coordinates |
| Auto-Tags | `src/topic_modeling.py` | ⏳ Ready to extract topics |
| Anomaly Detection | `src/anomaly_detection.py` | ⏳ Ready to find unique spots |

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

### ML Models (Planned)
| Model | Purpose |
|-------|---------|
| UMAP | 2D visualization for "vibe space" clustering |
| BERTopic | Auto-tagging from review text |
| Isolation Forest | Anomaly detection for unique spots |
| KMeans | Vibe clustering (legacy) |

---

## 📁 Key Files

### Backend (`src/`)
| File | Purpose |
|------|---------|
| `api.py` | FastAPI with lens calculations, custom endpoint |
| `hybrid_analysis.py` | NLP processing with gpt-5-nano (✅ complete) |
| `feature_engineering.py` | Aggregate signals to locations |
| `umap_viz.py` | UMAP dimensionality reduction |
| `topic_modeling.py` | BERTopic / keyword auto-tagging |
| `anomaly_detection.py` | Isolation Forest unique detection |

### Frontend
| File | Features |
|------|----------|
| `index.html` | Full UI: map, list, vibe map, custom lens builder |

---

## 🚀 Next Steps

```bash
# 1. Update location aggregates with new NLP data
python src/feature_engineering.py

# 2. Generate UMAP coordinates for Vibe Map clustering
python src/umap_viz.py

# 3. Auto-tag locations from review text
python src/topic_modeling.py --simple

# 4. Detect statistically unique places
python src/anomaly_detection.py
```

---

## 📊 Current Status

| Item | Status |
|------|--------|
| NLP Processing | ✅ 4,260/4,260 reviews complete |
| API | ✅ Running on localhost:8000 |
| Frontend | ✅ Running on localhost:5500 |
| Lenses | ✅ All working (Blended, Quality, Character, Underrated, Custom) |
| View Toggle | ✅ List / Vibe Map with zoom/pan |
| Vibe Map | ✅ Quality vs Character scatter plot |
| Feature Engineering | ⏳ Ready to run |
| UMAP Data | ⏳ Ready to generate |
| Auto-Tags | ⏳ Ready to generate |
| Anomaly Scores | ⏳ Ready to generate |
| GitHub | ✅ https://github.com/JeffBrines/dive-bar-detective |

---

## 🎯 Performance Notes

- **NLP Rate**: ~6 reviews/min with gpt-5-nano (~10 hours total)
- **Database**: 4,260 reviews across 251 locations
- **Vibe Map**: Auto-scales axes to data bounds, median-based quadrants
- **Custom Lens**: Real-time scoring with user-defined weights
