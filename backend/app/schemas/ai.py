"""Pydantic schemas for PCOS360 AI Engine endpoints."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class AIChatMessage(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'assistant'")
    content: str = Field(..., min_length=1, max_length=4000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        cleaned = v.strip().lower()
        if cleaned not in ("user", "assistant", "system"):
            raise ValueError("Role must be 'user', 'assistant', or 'system'.")
        return cleaned


class AIChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(..., min_length=1, max_length=4000, description="User question or health prompt")
    conversation_history: List[AIChatMessage] = Field(default_factory=list, description="Prior conversation context")
    include_context: bool = Field(True, description="Whether to include authentic user health context")
    focus_domain: Optional[str] = Field(None, max_length=50, description="Optional focus area (cycles, symptoms, labs, lifestyle)")

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned:
            raise ValueError("Message cannot be empty or whitespace only.")
        return cleaned


class AIInsightsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeframe_days: int = Field(30, ge=7, le=365, description="Days of history to analyze")
    include_correlations: bool = Field(True, description="Whether to run statistical symptom-lifestyle correlations")
    include_rotterdam_summary: bool = Field(True, description="Whether to evaluate educational Rotterdam criteria")


class AICopilotRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    action: str = Field(
        "daily_briefing",
        description="Action type: 'daily_briefing', 'symptom_check', 'lab_review', 'lifestyle_coaching', or 'consultation_packet'",
    )
    user_query: Optional[str] = Field(None, max_length=2000, description="Optional custom user instruction")

    @field_validator("action")
    @classmethod
    def validate_action(cls, v: str) -> str:
        allowed = {"daily_briefing", "symptom_check", "lab_review", "lifestyle_coaching", "consultation_packet"}
        cleaned = v.strip().lower()
        if cleaned not in allowed:
            raise ValueError(f"Action must be one of: {', '.join(sorted(allowed))}")
        return cleaned


class AIResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    status: str = Field(..., description="'success', 'emergency_escalation', 'provider_unavailable', or 'partial_deterministic'")
    response_text: str = Field(..., description="AI generated or deterministic clinical response")
    provider_used: Optional[str] = Field(None, description="'gemini', 'groq', 'deterministic_fallback', or None")
    model_used: Optional[str] = Field(None, description="Exact model name used for generation")
    is_personalized: bool = Field(False, description="True if authenticated user records were incorporated")
    red_flags_detected: bool = Field(False, description="True if acute clinical red flags were detected")
    urgency_level: str = Field("ROUTINE", description="'ROUTINE' or 'URGENT_EVALUATION_RECOMMENDED'")
    emergency_escalation_message: Optional[str] = Field(None, description="Immediate triage guidance when red flags exist")
    missing_data_noted: List[str] = Field(default_factory=list, description="Clinical data gaps identified")
    citations: List[str] = Field(default_factory=list, description="Medical guidelines and literature citations")
    deterministic_insights: Optional[Dict[str, Any]] = Field(None, description="Mathematical calculations & biomarker evaluations")
    disclaimer: str = Field(
        "Educational decision-support only. This information is not an automated medical diagnosis, "
        "prescription, or substitute for individualized clinical care by a licensed physician.",
        description="Mandatory medical safety disclaimer",
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

