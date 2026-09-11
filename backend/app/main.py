import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import models, seed
from .database import engine, SessionLocal
from .routers import experiments, phase1, demo, tester, trials, media, admin

models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="ADAPT API", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://ratesense.onrender.com",  
        "http://127.0.0.1:5173",          
        "http://localhost:5173",   
        "http://127.0.0.1:5500",
        "http://localhost:5500",
        "http://127.0.0.1:8123",     
        "http://localhost:8123"       
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition", "X-Admin-Token"],
)

app.include_router(experiments.router)
app.include_router(phase1.router)
app.include_router(demo.router)
app.include_router(trials.router)
app.include_router(media.router)
app.include_router(tester.router)
app.include_router(admin.router)

MEDIA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "media")
os.makedirs(MEDIA_DIR, exist_ok=True)
os.makedirs(os.path.join(MEDIA_DIR, "recordings"), exist_ok=True)
app.mount("/media", StaticFiles(directory=MEDIA_DIR), name="media")


@app.on_event("startup")
def on_startup():
    db = SessionLocal()
    try:
        seed.seed_media(db)
    finally:
        db.close()


@app.get("/api/v1/health")
def health():
    return {"success": True, "message": "ADAPT API is running.", "data": {}}
