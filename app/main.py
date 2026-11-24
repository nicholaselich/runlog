from fastapi import Depends, FastAPI
from sqlalchemy.orm import Session
from app.db import get_db
from app.routers import activities

app = FastAPI()
app.include_router(activities.router, prefix="/v1")

@app.get("/health")
def health():
    return {"status": "ok"}


