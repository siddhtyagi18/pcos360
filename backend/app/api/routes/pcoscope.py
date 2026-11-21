"""PCOSCOPE Health Intelligence & Pattern Discovery API routes.

Provides authenticated endpoints for:
1. GET /api/pcoscope/analysis: Deterministic pattern discovery (Cycle rhythms, symptom clusters,
   lifestyle correlations with N >= 7 guard, biomarker trajectories, care gaps, data completeness).
2. GET /api/pcoscope/insights: Comprehensive AI narrative synthesis combining deterministic
   discovery with LLM reasoning and clinician discussion points.
"""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.pcoscope import PcoscopeAnalysisResponse, PcoscopeInsightsResponse
from app.services.pcoscope_engine import (
    generate_pcoscope_insights,
    run_pcoscope_analysis,
)

router = APIRouter(prefix="/pcoscope", tags=["PCOSCOPE Pattern Discovery"])


@router.get("/analysis", response_model=PcoscopeAnalysisResponse, status_code=status.HTTP_200_OK)
def get_pcoscope_analysis(
    window_days: int = Query(30, ge=7, le=365, description="Rolling time window for symptom analysis in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve authentic deterministic pattern discovery analysis for the authenticated user.

    - Strictly uses PostgreSQL records for the authenticated user.
    - Menstrual cycle rhythm and variance analysis (Monash 2023 guideline thresholds).
    - Estimated menstrual cycle phase clearly identified; never asserts unconfirmed ovulation.
    - Rolling symptom clustering and temporal progression.
    - Lifestyle-symptom correlation matrix with strict N >= 7 data-quality threshold.
    - Longitudinal biomarker trajectory analysis across sequential lab reports.
    - Evidence-based clinical care gaps and profile data completeness score (0-100%).
    """
    return run_pcoscope_analysis(db=db, user=current_user, window_days=window_days)


@router.get("/insights", response_model=PcoscopeInsightsResponse, status_code=status.HTTP_200_OK)
def get_pcoscope_insights(
    window_days: int = Query(30, ge=7, le=365, description="Rolling time window for symptom analysis in days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve personalized AI narrative synthesis grounded in deterministic PCOSCOPE discovery.

    - Integrates authentic cycle, symptom, lifestyle, and biomarker patterns into clinical prompt.
    - Primary provider: Google Gemini API (gemini-flash-lite-latest); secondary: Groq API.
    - Gracefully falls back to deterministic clinical narrative if external LLMs are unreachable.
    - Returns structured key observations and tailored physician discussion points.
    """
    return generate_pcoscope_insights(db=db, user=current_user, window_days=window_days)

