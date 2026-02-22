import asyncio
import logging

from fastapi import APIRouter, BackgroundTasks, HTTPException

from app.models.schemas import AnalysisCreate, AnalysisStatus, AnalysisSummary
from app.services.analysis_engine import run_analysis
from app.services.supabase_client import get_supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/analyses", response_model=AnalysisStatus)
async def create_analysis(
    body: AnalysisCreate, background_tasks: BackgroundTasks
):
    """Start a new analysis for a brand URL."""
    db = get_supabase()

    # Create analysis record
    result = (
        db.table("analyses")
        .insert({"brand_url": body.brand_url, "status": "pending"})
        .execute()
    )
    analysis = result.data[0]

    # Run analysis in background
    background_tasks.add_task(
        _run_analysis_wrapper, analysis["id"], body.brand_url
    )

    return AnalysisStatus(
        id=analysis["id"],
        status=analysis["status"],
        brand_url=analysis["brand_url"],
        brand_name=analysis.get("brand_name"),
        created_at=analysis["created_at"],
        completed_at=analysis.get("completed_at"),
    )


async def _run_analysis_wrapper(analysis_id: str, brand_url: str):
    """Wrapper to run analysis in background with proper async context."""
    try:
        await run_analysis(analysis_id, brand_url)
    except Exception as e:
        logger.error(f"Background analysis failed: {e}")


@router.get("/analyses", response_model=list[AnalysisSummary])
async def list_analyses():
    """List all analyses, most recent first."""
    db = get_supabase()
    result = (
        db.table("analyses")
        .select("*")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )
    return [
        AnalysisSummary(
            id=a["id"],
            brand_url=a["brand_url"],
            brand_name=a.get("brand_name"),
            status=a["status"],
            created_at=a["created_at"],
            completed_at=a.get("completed_at"),
        )
        for a in result.data
    ]


@router.get("/analyses/{analysis_id}", response_model=AnalysisStatus)
async def get_analysis(analysis_id: str):
    """Get analysis details."""
    db = get_supabase()
    result = (
        db.table("analyses").select("*").eq("id", analysis_id).execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")

    a = result.data[0]
    return AnalysisStatus(
        id=a["id"],
        status=a["status"],
        brand_url=a["brand_url"],
        brand_name=a.get("brand_name"),
        created_at=a["created_at"],
        completed_at=a.get("completed_at"),
    )


@router.get("/analyses/{analysis_id}/status")
async def get_analysis_status(analysis_id: str):
    """Get analysis status (lightweight endpoint for polling)."""
    db = get_supabase()
    result = (
        db.table("analyses")
        .select("id, status, brand_name, completed_at, progress")
        .eq("id", analysis_id)
        .execute()
    )
    if not result.data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    return result.data[0]
