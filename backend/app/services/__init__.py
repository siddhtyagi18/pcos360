"""Application domain services, deterministic clinical calculators, and context engine."""

from app.services.clinical_calculator import (
    BiomarkerEvaluationResult,
    CorrelationPairResult,
    CycleAnalysisResult,
    RotterdamAssessmentResult,
    assess_rotterdam_criteria_educational,
    calculate_cycle_statistics,
    calculate_pearson_correlation,
    calculate_symptom_correlations,
    evaluate_biomarker,
    screen_urgent_symptoms,
)
from app.services.context_builder import (
    ClinicalRecordData,
    ContextBuilderDatabaseError,
    ContextBuilderError,
    CycleData,
    DataFreshness,
    HealthProfileData,
    LabReportData,
    LifestyleData,
    SymptomData,
    UserHealthContext,
    UserNotFoundError,
    build_user_health_context,
    build_user_health_context_by_id,
)
from app.services.ai_engine import (
    AIEngineError,
    generate_chat_response,
    generate_copilot_response,
    generate_insights_response,
)
from app.services.pcoscope_engine import (
    analyze_biomarker_trajectories,
    analyze_cycle_patterns,
    analyze_lifestyle_correlations,
    analyze_symptom_trends,
    calculate_data_completeness,
    evaluate_care_gaps,
    generate_pcoscope_insights,
    run_pcoscope_analysis,
)

__all__ = [
    # Clinical Calculators
    "CycleAnalysisResult",
    "CorrelationPairResult",
    "BiomarkerEvaluationResult",
    "RotterdamAssessmentResult",
    "calculate_cycle_statistics",
    "calculate_pearson_correlation",
    "calculate_symptom_correlations",
    "evaluate_biomarker",
    "assess_rotterdam_criteria_educational",
    "screen_urgent_symptoms",
    # Context Engine
    "DataFreshness",
    "HealthProfileData",
    "CycleData",
    "SymptomData",
    "LifestyleData",
    "LabReportData",
    "ClinicalRecordData",
    "UserHealthContext",
    "ContextBuilderError",
    "ContextBuilderDatabaseError",
    "UserNotFoundError",
    "build_user_health_context",
    "build_user_health_context_by_id",
    # AI Engine
    "AIEngineError",
    "generate_chat_response",
    "generate_insights_response",
    "generate_copilot_response",
    # PCOSCOPE Engine
    "analyze_biomarker_trajectories",
    "analyze_cycle_patterns",
    "analyze_lifestyle_correlations",
    "analyze_symptom_trends",
    "calculate_data_completeness",
    "evaluate_care_gaps",
    "generate_pcoscope_insights",
    "run_pcoscope_analysis",
]
