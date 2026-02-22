from pydantic import BaseModel, HttpUrl
from datetime import datetime
from typing import Optional


# --- Request schemas ---

class AnalysisCreate(BaseModel):
    brand_url: str


# --- Response schemas ---

class AnalysisStatus(BaseModel):
    id: str
    status: str
    brand_url: str
    brand_name: Optional[str] = None
    created_at: str
    completed_at: Optional[str] = None


class AnalysisSummary(BaseModel):
    id: str
    brand_url: str
    brand_name: Optional[str] = None
    status: str
    created_at: str
    completed_at: Optional[str] = None


class CompetitorResult(BaseModel):
    id: str
    name: str
    url: str
    domain: Optional[str] = None
    description: Optional[str] = None
    is_primary: bool = False
    visibility_score: Optional[float] = None
    share_of_voice: Optional[float] = None
    citation_count: Optional[int] = None
    avg_position: Optional[float] = None
    engines: Optional[dict] = None


class CitationResult(BaseModel):
    id: str
    engine: str
    cited_url: str
    cited_domain: Optional[str] = None
    cited_title: Optional[str] = None
    position: Optional[int] = None
    snippet: Optional[str] = None
    competitor_name: Optional[str] = None
    prompt_text: Optional[str] = None


class EngineScore(BaseModel):
    engine: str
    visibility_score: float
    share_of_voice: float
    citation_count: int
    avg_position: Optional[float] = None


class OverviewResponse(BaseModel):
    analysis_id: str
    brand_name: Optional[str] = None
    brand_url: str
    status: str
    overall_visibility: float
    overall_sov: float
    total_citations: int
    engines: list[EngineScore]
    competitor_count: int
    prompt_count: int


class CompetitorListResponse(BaseModel):
    competitors: list[CompetitorResult]


class CitationListResponse(BaseModel):
    citations: list[CitationResult]
    total: int


class EngineBreakdownResponse(BaseModel):
    engines: list[EngineScore]
    brand_scores: dict  # engine -> score for the primary brand


class HistoryEntry(BaseModel):
    analysis_id: str
    created_at: str
    visibility_score: float
    share_of_voice: float
    citation_count: int


class HistoryResponse(BaseModel):
    brand_url: str
    entries: list[HistoryEntry]


class PromptResultEntry(BaseModel):
    prompt_id: str
    prompt_text: str
    category: Optional[str] = None
    citations: list[CitationResult]


class PromptResultsResponse(BaseModel):
    prompts: list[PromptResultEntry]
