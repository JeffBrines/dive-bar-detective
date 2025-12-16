# Dive Bar Detective

## Overview
A web application that helps users discover dive bars and hidden gems in Denver. Uses machine learning and sentiment analysis to analyze Google reviews and provide unique scoring metrics.

## Project Structure
- `src/api.py` - FastAPI backend serving both API endpoints and static frontend
- `index.html` - Single-page frontend application with map and filters
- `src/` - Python modules for data collection, ML models, and analysis (not required for running the app)

## Running the App
The application runs on port 5000 using uvicorn:
```bash
uvicorn src.api:app --host 0.0.0.0 --port 5000 --reload
```

## Required Environment Variables
- `SUPABASE_URL` - Supabase project URL
- `SUPABASE_KEY` - Supabase anon key

## Tech Stack
- **Backend**: FastAPI, Python 3.11
- **Database**: Supabase (PostgreSQL)
- **Frontend**: Vanilla JavaScript, Leaflet.js for maps, Chart.js for visualizations

## Key Features
- Location scoring with multiple "lenses" (Blended, Quality, Character, Underrated)
- Interactive map with place markers
- Review sentiment analysis
- Custom lens builder for personalized scoring

## Deployment
Configured for autoscale deployment using gunicorn with uvicorn workers.

**Build uses `requirements-production.txt`** (~700MB) instead of `requirements.txt` (~5GB+).

The production file excludes heavy ML packages (bertopic, transformers, scikit-learn, torch/CUDA) since the API only serves pre-computed data from Supabase. ML processing happens offline.

## Development vs Production Dependencies
- **requirements-production.txt** - Lightweight, for deployed web API (~100MB)
- **requirements-ml.txt** - Full ML stack, for local data processing scripts (renamed from requirements.txt to prevent auto-detection)
