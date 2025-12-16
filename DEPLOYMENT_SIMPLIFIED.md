# Simplified Single-Service Deployment 🚀

## What Changed

**Before**: Two separate services (backend + frontend static site)
**After**: One unified service serving both API and frontend

## Benefits

✅ **Simpler**: One service instead of two
✅ **Faster**: No cold start for separate frontend
✅ **No CORS**: Same-origin requests
✅ **One URL**: Everything at `dive-bar-detective.onrender.com`
✅ **Easier**: Less configuration, fewer moving parts

## How It Works

Your FastAPI backend now serves the `index.html` file at the root path (`/`), while API endpoints remain at their paths (`/locations`, `/vibes`, etc.).

```
https://dive-bar-detective.onrender.com/
  ├── /              → index.html (frontend)
  ├── /locations     → API endpoint
  ├── /vibes         → API endpoint
  └── /locations/:id → API endpoint
```

## Changes Made

### 1. `src/api.py`
- Added `FileResponse` import
- Root endpoint (`/`) now serves `index.html`
- Simplified CORS (no need for separate frontend URL)

### 2. `index.html`
- Simplified API URL detection
- Uses `window.location.origin` in production
- Still supports local dev with separate servers

### 3. `render.yaml`
- Removed separate static site service
- Single web service configuration
- Cleaner, more maintainable

## Deployment

Same as before, but even simpler:

```bash
git add .
git commit -m "Simplified single-service deployment"
git push origin main
```

Then on Render:
- New → Blueprint (or Web Service)
- One service created
- One URL to access everything

## Local Development

Still works the same way:

**Option 1: Separate servers (recommended for development)**
```bash
# Terminal 1: API
uvicorn src.api:app --reload --port 8000

# Terminal 2: Frontend
python3 -m http.server 5500
```

**Option 2: Single server (matches production)**
```bash
uvicorn src.api:app --reload --port 8000
# Visit http://localhost:8000
```

## Cost

Still **$0/month** on free tier!
- One service = 750 hours/month
- Sleeps after 15min inactivity
- 20-45s cold start

## Migration from Two-Service Setup

If you already deployed with two services:
1. Delete the static site service in Render dashboard
2. Push the updated code
3. Render will redeploy the backend (now serving frontend too)
4. Update any bookmarks to the new single URL

That's it! Much cleaner. 🎉





