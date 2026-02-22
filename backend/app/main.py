import logging

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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyses_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")


@app.get("/api/health")
async def health():
    return {"status": "ok"}
