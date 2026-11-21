"""Pydantic schemas for PCOSCOPE Health Intelligence & Pattern Discovery.

Strictly distinguishes between:
- Deterministic calculated metrics (exact mathematical calculations)
- Statistical associations (observational Pearson correlations with N >= 7 data-quality threshold)
- Educational assessments & care gaps (guideline-referenced clinical decision support)
- AI-synthesized narrative interpretations (LLM reasoning grounded in authentic context)
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CyclePatternMetrics(BaseModel):
    """Deterministic cycle rhythm, length variance, and estimated phase tracking."""
    model_config = ConfigDict(from_attributes=True)

    sample_size: int = Field(..., description="Number of authentic menstrual cycles recorded")
    has_sufficient_data: bool = Field(..., description="True if at least 3 cycles are logged for variance evaluation")
    mean_length_days: Optional[float] = Field(None, description="Average cycle length in days")
    median_length_days: Optional[float] = Field(None, description="Median cycle length in days")
    stdev_days: Optional[float] = Field(None, description="Cycle length standard deviation")
    min_length_days: Optional[int] = Field(None, description="Shortest observed cycle")
    max_length_days: Optional[int] = Field(None, description="Longest observed cycle")
    rhythm_classification: str = Field(
        ...,
        description="Regular (21-35d), Irregular (>35d or variable), Oligomenorrhea, Amenorrhea Flag, or Insufficient Data",
    )
    is_irregular: bool = Field(False, description="True if cycle variability or length violates Monash 2023 regularity")
    current_cycle_day: Optional[int] = Field(None, description="Days elapsed since the start of the latest period")
    estimated_current_phase: str = Field(
        ...,
        description="Calculated menstrual phase based on cycle calendar (Always explicitly labeled as ESTIMATED)",
    )
    ovulation_confirmation_status: str = Field(
        "UNCONFIRMED: Calendar estimation only. True ovulation confirmation requires mid-luteal serum progesterone (>= 3 ng/mL), validated LH peak test, or serial pelvic ultrasound follicular tracking.",
        description="Mandatory disclaimer that calendar estimates do not prove ovulation",
    )
    next_period_estimated: Optional[str] = Field(None, description="Estimated next period date based on mean cycle length")
    trend_direction: str = Field("Stable", description="Lengthening, Shortening, Stable, Variable, or Insufficient Data")
    clinical_interpretation: str = Field(..., description="Monash 2023 evidence-based guideline evaluation")
    guideline_reference: str = Field(
        "Monash 2023 International Evidence-Based Guideline for the Assessment and Management of PCOS",
        description="Clinical guideline reference",
    )


class SymptomClusterItem(BaseModel):
    """Aggregated symptom frequency and co-occurrence in rolling time windows."""
    model_config = ConfigDict(from_attributes=True)

    symptom_key: str = Field(..., description="Field name (e.g. acne, fatigue, pelvic_pain, bloating)")
    display_name: str = Field(..., description="Human-readable label")
    occurrences_count: int = Field(..., description="Number of days symptom was reported")
    total_window_days: int = Field(..., description="Total days in the analysis window")
    prevalence_pct: float = Field(..., description="Percentage of logged days symptom was present")
    average_severity: float = Field(..., description="Average severity score on a normalized 0-10 scale")
    severity_label: str = Field(..., description="Mild (1-3), Moderate (4-6), or Severe (7-10)")
    trend_direction: str = Field("Insufficient Data", description="Increasing, Decreasing, Stable, or Insufficient Data")
    co_occurring_symptoms: List[str] = Field(
        default_factory=list,
        description="Other symptoms frequently reported on the same days",
    )


class SymptomTrendsAnalysis(BaseModel):
    """Multi-window symptom clustering and temporal progression."""
    model_config = ConfigDict(from_attributes=True)

    window_days: int = Field(..., description="Evaluation window duration in days (e.g. 30, 90)")
    total_logged_days: int = Field(..., description="Actual daily symptom entries in this window")
    top_clusters: List[SymptomClusterItem] = Field(default_factory=list, description="Ranked symptom clusters")
    temporal_timeline: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological time series formatted for UI charting",
    )
    summary_note: str = Field(..., description="Clinical summary of symptom burden")


class LifestyleCorrelationItem(BaseModel):
    """Statistical association between lifestyle habits and daily symptoms.
    
    Treats N >= 7 as a minimum data-quality threshold, NOT a guarantee of statistical significance.
    """
    model_config = ConfigDict(from_attributes=True)

    factor_a: str = Field(..., description="Lifestyle factor (e.g., Sleep Duration, Stress Level, Exercise)")
    factor_b: str = Field(..., description="Symptom or outcome (e.g., Fatigue Severity, Acne, Bloating)")
    sample_size: int = Field(..., description="Number of paired daily observations (N)")
    has_sufficient_data: bool = Field(..., description="True if sample size N >= 7")
    correlation_coefficient: Optional[float] = Field(
        None,
        description="Pearson r value (-1.0 to +1.0) when N >= 7; None if sample size is insufficient",
    )
    direction: Optional[str] = Field(None, description="Positive, Negative, or None")
    strength: Optional[str] = Field(None, description="Strong, Moderate, Weak, or None")
    data_quality_status: str = Field(
        ...,
        description="'Sufficient data quality (N >= 7)' or 'Insufficient sample size (N < 7)'",
    )
    significance_warning: str = Field(
        ...,
        description="Explicit notice regarding sample size and clinical validity",
    )
    interpretation: str = Field(..., description="Clinical interpretation of the statistical observation")
    caveat: str = Field(
        "Observational correlation only. Statistical association does not establish medical causation or clinical efficacy. Confounding factors such as medications, cycle phase, and diet must be considered.",
        description="Mandatory scientific disclaimer",
    )


class BiomarkerTrajectoryItem(BaseModel):
    """Historical progression of a laboratory biomarker across sequential reports."""
    model_config = ConfigDict(from_attributes=True)

    biomarker_name: str = Field(..., description="Reported or standard test name")
    canonical_name: str = Field(..., description="Standardized biomarker identifier")
    datapoints_count: int = Field(..., description="Number of recorded lab values")
    latest_value: Optional[float] = Field(None, description="Most recent quantitative result")
    latest_unit: Optional[str] = Field(None, description="Unit of measurement")
    latest_status: str = Field("Not Tested", description="Normal, Borderline / Impaired, Elevated, Low, or Indeterminate")
    latest_date: Optional[str] = Field(None, description="Date of latest lab report")
    reference_interval: str = Field(..., description="Standard clinical reference interval")
    trajectory_trend: str = Field(
        "Single Data Point",
        description="Improving, Worsening, Stable, Single Data Point, or Not Tested",
    )
    history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Chronological history of values with date, value, status, and unit",
    )
    clinical_significance: str = Field(..., description="Why this biomarker matters in PCOS evaluation")


class CareGapItem(BaseModel):
    """Evidence-based clinical care gap identifying missing tests or documentation."""
    model_config = ConfigDict(from_attributes=True)

    category: str = Field(..., description="Laboratory, Cycle Tracking, Daily Symptoms, or Clinical Profile")
    title: str = Field(..., description="Short actionable description of missing care element")
    description: str = Field(..., description="Detailed medical context and recommended action")
    priority: str = Field("Medium", description="High, Medium, or Low")
    guideline_source: str = Field(..., description="Reference guideline (e.g. Monash 2023, Endocrine Society 2013)")


class DataCompletenessSummary(BaseModel):
    """Objective assessment of patient record completeness in PostgreSQL."""
    model_config = ConfigDict(from_attributes=True)

    overall_score_pct: int = Field(..., ge=0, le=100, description="Overall profile data maturity percentage")
    profile_initialized: bool = Field(..., description="True if age, height, weight are documented")
    cycles_logged_count: int = Field(..., description="Total cycles in database")
    symptoms_logged_days: int = Field(..., description="Total symptom log dates")
    lifestyle_logged_days: int = Field(..., description="Total lifestyle log dates")
    lab_biomarkers_count: int = Field(..., description="Total quantitative biomarkers recorded")
    missing_critical_elements: List[str] = Field(default_factory=list, description="Missing clinical parameters")
    recommendation: str = Field(..., description="Next suggested logging activity to improve personal insight fidelity")


class PcoscopeAnalysisResponse(BaseModel):
    """Complete deterministic PCOSCOPE pattern discovery analysis."""
    model_config = ConfigDict(from_attributes=True)

    user_id: int = Field(..., description="Authenticated user ID")
    analysis_timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    data_completeness: DataCompletenessSummary = Field(..., description="Record completeness summary")
    cycle_patterns: CyclePatternMetrics = Field(..., description="Menstrual regularity and estimated phase")
    symptom_trends: SymptomTrendsAnalysis = Field(..., description="Symptom clusters and temporal progression")
    lifestyle_correlations: List[LifestyleCorrelationItem] = Field(
        default_factory=list,
        description="Statistical associations with N >= 7 quality threshold",
    )
    biomarker_trajectories: List[BiomarkerTrajectoryItem] = Field(
        default_factory=list,
        description="Historical lab biomarker trends and monitoring gaps",
    )
    care_gaps: List[CareGapItem] = Field(default_factory=list, description="Actionable clinical care gaps")
    rotterdam_assessment: Dict[str, Any] = Field(
        default_factory=dict,
        description="Educational Rotterdam criteria evaluation (Decision support, not automated diagnosis)",
    )
    urgent_red_flags: Dict[str, Any] = Field(
        default_factory=dict,
        description="Urgent symptom safety evaluation",
    )
    disclaimer: str = Field(
        "Educational medical decision-support only. Deterministic calculations, statistical correlations, and pattern "
        "discoveries are provided for informed discussions with licensed healthcare providers and do not constitute an "
        "automated medical diagnosis or prescription.",
        description="Mandatory medical safety disclaimer",
    )


class PcoscopeInsightsResponse(BaseModel):
    """PCOSCOPE pattern discovery combined with personalized AI narrative synthesis."""
    model_config = ConfigDict(from_attributes=True)

    analysis: PcoscopeAnalysisResponse = Field(..., description="Underlying deterministic pattern discovery metrics")
    narrative_summary: str = Field(..., description="AI synthesized or clinical fallback overview")
    key_observations: List[str] = Field(default_factory=list, description="High-priority patient observations")
    doctor_discussion_points: List[str] = Field(
        default_factory=list,
        description="Tailored clinical questions for the patient's next physician appointment",
    )
    provider_used: Optional[str] = Field(None, description="'gemini', 'groq', or 'deterministic_fallback'")
    model_used: Optional[str] = Field(None, description="Model identifier used for generation")
    is_ai_generated: bool = Field(False, description="True if response generated by an external LLM")
    disclaimer: str = Field(
        "Educational decision-support only. This synthesis is not an automated medical diagnosis, "
        "prescription, or substitute for individualized clinical care by a licensed physician.",
        description="Mandatory medical safety disclaimer",
    )
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

