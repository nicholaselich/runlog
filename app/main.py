from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.routers import activities, stats

app = FastAPI()
app.include_router(activities.router, prefix="/v1")
app.include_router(stats.router, prefix="/v1")

@app.get("/health")
def health():
    return {"status": "ok"}

# Serve the frontend from the same origin as the API.
DASHBOARD_DIR = Path(__file__).resolve().parent.parent / "dashboard"
app.mount("/dashboard", StaticFiles(directory=DASHBOARD_DIR, html=True), name="dashboard")
