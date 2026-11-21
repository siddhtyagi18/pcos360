"""AI Intelligence Engine API routes.

Provides authenticated endpoints for conversational chat, comprehensive clinical insights,
and targeted copilot guidance, strictly grounded in the authenticated user's health context.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.ai import (
    AIChatRequest,
    AICopilotRequest,
    AIInsightsRequest,
    AIResponse,
)
from app.services.ai_engine import (
    generate_chat_response,
    generate_copilot_response,
    generate_insights_response,
)

router = APIRouter(prefix="/ai", tags=["AI Health Intelligence"])


@router.post("/chat", response_model=AIResponse, status_code=status.HTTP_200_OK)
def chat_with_ai(
    payload: AIChatRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Personalized, evidence-grounded conversational AI interaction.

    - Authenticated access only (Bearer JWT).
    - Incorporates user's actual health context (cycles, symptoms, labs, lifestyle).
    - Pre-screens for acute medical red flags and provides emergency triage warnings.
    - Gracefully degrades to deterministic clinical summary if external LLMs are unreachable.
    """
    return generate_chat_response(db=db, user=current_user, request=payload)


@router.post("/insights", response_model=AIResponse, status_code=status.HTTP_200_OK)
def generate_insights(
    payload: AIInsightsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generate comprehensive clinical health insights synthesizing cycles, biomarkers, and lifestyle.

    - Evaluates Monash 2023 cycle patterns and variance.
    - Evaluates laboratory biomarkers against reported and guideline intervals.
    - Runs statistical symptom-lifestyle correlations with sample size validation.
    - Assesses educational Rotterdam criteria and identifies missing documentation.
    """
    return generate_insights_response(db=db, user=current_user, request=payload)


@router.post("/copilot", response_model=AIResponse, status_code=status.HTTP_200_OK)
def copilot_action(
    payload: AICopilotRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Targeted AI copilot actions: daily_briefing, symptom_check, lab_review, lifestyle_coaching."""
    return generate_copilot_response(db=db, user=current_user, request=payload)

