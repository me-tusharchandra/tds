import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S",
)

from app.api.analyses import router as analyses_router
from app.api.dashboard import router as dashboard_router

app = FastAPI(title="TDS - AI Search Visibility Analytics", version="1.0.0")

# CORS: configurable via CORS_ORIGINS env var (comma-separated), defaults to localhost:3000
_default_origins = ["http://localhost:3000"]
_cors_origins = os.getenv("CORS_ORIGINS", "").strip()
allowed_origins = [o.strip() for o in _cors_origins.split(",") if o.strip()] if _cors_origins else _default_origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyses_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
