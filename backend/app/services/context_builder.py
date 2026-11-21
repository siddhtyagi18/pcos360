"""User Health Context Engine for PCOS360.

Retrieves authentic patient health data from PostgreSQL across all clinical modules,
performs deterministic clinical calculations, and formats comprehensive, structured
context with data freshness, provenance, and explicit missing-data tracking.

SECURITY & CLINICAL SAFETY GUARANTEES:
1. Strict User Isolation: All database queries filter strictly by the verified session user_id.
2. Anti-Fabrication: Never generates fake biomarker values, sample cycles, or mock history.
3. Transparent Gaps: Explicitly documents missing clinical information, unrecorded tests,
   and insufficient sample sizes.
4. Privacy: Application logs only record operational counters; patient health data and
   identifiers are never exposed in log output.
5. Educational Decision Support: Outputs structured clinical context for downstream reasoning;
   never automates a medical diagnosis.
"""

from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.medical_knowledge import DEFAULT_BIOMARKER_RANGES
from app.models.clinical_record import ClinicalRecord
from app.models.daily_symptom import DailySymptom
from app.models.health_profile import HealthProfile
from app.models.lab_report import LabReport
from app.models.lifestyle_log import LifestyleLog
from app.models.menstrual_cycle import MenstrualCycle
from app.models.user import User
from app.services.clinical_calculator import (
    assess_rotterdam_criteria_educational,
    calculate_cycle_statistics,
    calculate_symptom_correlations,
    evaluate_biomarker,
    screen_urgent_symptoms,
)

logger = logging.getLogger("pcos360.context_builder")


class ContextBuilderError(Exception):
    """Base exception for user context engine errors."""
    pass


class ContextBuilderDatabaseError(ContextBuilderError):
    """Raised when an unrecoverable database error occurs while loading user context."""
    pass


class UserNotFoundError(ContextBuilderError):
    """Raised when the specified user account does not exist."""
    pass


# ==============================================================================
# Structured Data Context Containers
# ==============================================================================

@dataclass
class DataFreshness:
    profile_updated_at: Optional[str] = None
    latest_cycle_date: Optional[str] = None
    latest_symptom_date: Optional[str] = None
    latest_lifestyle_date: Optional[str] = None
    latest_lab_date: Optional[str] = None
    latest_clinical_record_date: Optional[str] = None
    most_recent_activity_date: Optional[str] = None
    days_since_latest_activity: Optional[int] = None


@dataclass
class HealthProfileData:
    is_present: bool = False
    age: Optional[int] = None
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    calculated_bmi: Optional[float] = None
    bmi_category: Optional[str] = None
    diagnosis_status: Optional[str] = None
    diagnosis_year: Optional[int] = None
    existing_conditions: List[str] = field(default_factory=list)
    medications: List[str] = field(default_factory=list)
    last_updated: Optional[str] = None
    missing_fields: List[str] = field(default_factory=list)
    source: str = "health_profiles (self-reported)"


@dataclass
class CycleData:
    is_present: bool = False
    total_recorded_cycles: int = 0
    latest_cycle_start: Optional[str] = None
    days_since_latest_period: Optional[int] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    statistics: Dict[str, Any] = field(default_factory=dict)
    missing_data_note: Optional[str] = None
    source: str = "menstrual_cycles (calendar tracking)"


@dataclass
class SymptomData:
    is_present: bool = False
    total_logged_days: int = 0
    date_range_start: Optional[str] = None
    date_range_end: Optional[str] = None
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)
    symptom_summary: Dict[str, Any] = field(default_factory=dict)
    red_flag_screening: Dict[str, Any] = field(default_factory=dict)
    missing_data_note: Optional[str] = None
    source: str = "daily_symptoms (daily tracking)"


@dataclass
class LifestyleData:
    is_present: bool = False
    total_logged_days: int = 0
    recent_logs: List[Dict[str, Any]] = field(default_factory=list)
    averages: Dict[str, Optional[float]] = field(default_factory=dict)
    correlations: List[Dict[str, Any]] = field(default_factory=list)
    missing_data_note: Optional[str] = None
    source: str = "lifestyle_logs (daily tracking)"


@dataclass
class LabReportData:
    is_present: bool = False
    total_biomarkers_recorded: int = 0
    latest_report_date: Optional[str] = None
    evaluated_biomarkers: List[Dict[str, Any]] = field(default_factory=list)
    abnormal_biomarkers: List[Dict[str, Any]] = field(default_factory=list)
    missing_critical_pcos_biomarkers: List[str] = field(default_factory=list)
    missing_data_note: Optional[str] = None
    source: str = "lab_reports (laboratory panels)"


@dataclass
class ClinicalRecordData:
    is_present: bool = False
    total_records: int = 0
    latest_record_date: Optional[str] = None
    records: List[Dict[str, Any]] = field(default_factory=list)
    rotterdam_assessment: Dict[str, Any] = field(default_factory=dict)
    missing_data_note: Optional[str] = None
    source: str = "clinical_records (clinical documentation)"


@dataclass
class UserHealthContext:
    user_id: int
    generated_at: str
    freshness: DataFreshness
    profile: HealthProfileData
    cycles: CycleData
    symptoms: SymptomData
    lifestyle: LifestyleData
    labs: LabReportData
    clinical: ClinicalRecordData
    missing_data_summary: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete context to a JSON-compatible dictionary."""
        return asdict(self)

    def to_clinical_prompt_text(self) -> str:
        """Render a concise, strictly de-identified clinical summary for downstream AI prompts.

        Excludes all user PII (no name, email, or database IDs).
        Explicitly identifies missing clinical domains to prevent AI hallucination.
        """
        lines: List[str] = [
            f"# CLINICAL HEALTH CONTEXT (Generated UTC: {self.generated_at})",
            "## 1. Patient Profile & Demographics",
        ]

        # Profile
        if self.profile.is_present:
            age_str = f"{self.profile.age} years" if self.profile.age is not None else "Not reported"
            bmi_str = (
                f"{self.profile.calculated_bmi} kg/m² ({self.profile.bmi_category})"
                if self.profile.calculated_bmi is not None
                else "Not calculated"
            )
            dx_str = self.profile.diagnosis_status or "Unspecified"
            if self.profile.diagnosis_year:
                dx_str += f" (since {self.profile.diagnosis_year})"
            conds_str = ", ".join(self.profile.existing_conditions) if self.profile.existing_conditions else "None reported"
            meds_str = ", ".join(self.profile.medications) if self.profile.medications else "None reported"

            lines.extend([
                f"- Age: {age_str}",
                f"- BMI: {bmi_str}",
                f"- PCOS Diagnosis Status: {dx_str}",
                f"- Existing Conditions: {conds_str}",
                f"- Active Medications: {meds_str}",
            ])
            if self.profile.missing_fields:
                lines.append(f"- Incomplete Profile Fields: {', '.join(self.profile.missing_fields)}")
        else:
            lines.append("- Profile: NOT INITIALIZED (Demographics, BMI, and baseline status missing)")

        # Cycles
        lines.append("\n## 2. Menstrual Cycle History")
        if self.cycles.is_present and self.cycles.total_recorded_cycles > 0:
            stats = self.cycles.statistics
            lines.extend([
                f"- Cycles Recorded: {self.cycles.total_recorded_cycles}",
                f"- Latest Cycle Start: {self.cycles.latest_cycle_start or 'Unknown'}",
                f"- Days Since Last Period: {self.cycles.days_since_latest_period if self.cycles.days_since_latest_period is not None else 'Unknown'}",
                f"- Rhythm Classification: {stats.get('rhythm_classification', 'Unknown')}",
                f"- Mean Cycle Length: {stats.get('mean_length', 'N/A')} days (SD: {stats.get('stdev_length', 'N/A')})",
                f"- Clinical Interpretation: {stats.get('clinical_interpretation', 'N/A')}",
            ])
            if stats.get("has_amenorrhea_flag"):
                lines.append("- ⚠️ AMENORRHEA FLAG: Cycle interval >= 90 days detected.")
        else:
            lines.append(f"- Cycle History: {self.cycles.missing_data_note or 'NO CYCLES LOGGED'}")

        # Symptoms
        lines.append("\n## 3. Symptom Tracking & Red-Flag Screening")
        if self.symptoms.is_present:
            lines.extend([
                f"- Logged Days Analyzed: {self.symptoms.total_logged_days}",
                f"- Tracking Span: {self.symptoms.date_range_start or 'N/A'} to {self.symptoms.date_range_end or 'N/A'}",
            ])
            summary = self.symptoms.symptom_summary
            if summary:
                lines.append(f"- Symptom Overview: {summary}")
            rf = self.symptoms.red_flag_screening
            if rf.get("has_urgent_symptoms"):
                lines.append(f"- ⚠️ URGENT CLINICAL RED FLAG DETECTED: {rf.get('escalation_message')}")
            else:
                lines.append("- Red-Flag Screening: No urgent clinical red flags detected in current logs.")
        else:
            lines.append(f"- Symptom History: {self.symptoms.missing_data_note or 'NO SYMPTOMS LOGGED'}")

        # Lifestyle
        lines.append("\n## 4. Lifestyle Metrics & Mathematical Correlations")
        if self.lifestyle.is_present:
            avg = self.lifestyle.averages
            lines.extend([
                f"- Lifestyle Logs: {self.lifestyle.total_logged_days} days recorded",
                f"- Averages: Sleep {avg.get('avg_sleep_hours', 'N/A')} hrs/night, "
                f"Stress {avg.get('avg_stress_level', 'N/A')}/5, "
                f"Water {avg.get('avg_water_intake', 'N/A')} units, "
                f"Exercise {avg.get('avg_exercise_minutes', 'N/A')} mins/day",
            ])
            corrs = self.lifestyle.correlations
            valid_corrs = [c for c in corrs if c.get("has_sufficient_data")]
            if valid_corrs:
                lines.append("- Statistically Sufficient Correlations (N >= 7):")
                for c in valid_corrs:
                    lines.append(
                        f"  * {c.get('factor_a')} vs {c.get('factor_b')}: "
                        f"r={c.get('correlation_coefficient')}, {c.get('strength')} {c.get('direction')} ({c.get('interpretation')})"
                    )
            else:
                lines.append("- Mathematical Correlations: Insufficient paired daily observations (< 7 days) to assert correlation.")
        else:
            lines.append(f"- Lifestyle History: {self.lifestyle.missing_data_note or 'NO LIFESTYLE LOGS'}")

        # Labs
        lines.append("\n## 5. Laboratory Biomarkers")
        if self.labs.is_present and self.labs.evaluated_biomarkers:
            lines.append(f"- Biomarkers Logged: {self.labs.total_biomarkers_recorded} entries (Latest: {self.labs.latest_report_date or 'N/A'})")
            if self.labs.abnormal_biomarkers:
                lines.append("- Out-of-Range Biomarkers:")
                for b in self.labs.abnormal_biomarkers:
                    lines.append(
                        f"  * {b.get('canonical_name')}: {b.get('numeric_value')} {b.get('reported_unit') or b.get('standard_unit')} "
                        f"[Ref: {b.get('reference_interval_applied')}] — Status: {b.get('status')}"
                    )
            else:
                lines.append("- All recorded biomarkers fall within reference intervals.")

            if self.labs.missing_critical_pcos_biomarkers:
                lines.append(f"- Unrecorded Key PCOS Biomarkers: {', '.join(self.labs.missing_critical_pcos_biomarkers[:6])}")
        else:
            lines.append(f"- Laboratory Reports: {self.labs.missing_data_note or 'NO LAB REPORTS ON FILE'}")

        # Clinical Records & Rotterdam
        lines.append("\n## 6. Clinical Records & Educational Rotterdam Assessment")
        if self.clinical.is_present and self.clinical.total_records > 0:
            lines.append(f"- Clinical Records: {self.clinical.total_records} documents on file (Latest: {self.clinical.latest_record_date or 'N/A'})")
        else:
            lines.append(f"- Clinical Records: {self.clinical.missing_data_note or 'NO CLINICAL DOCUMENTS'}")

        rotterdam = self.clinical.rotterdam_assessment
        if rotterdam:
            lines.extend([
                f"- Rotterdam Educational Phenotype: {rotterdam.get('educational_phenotype_alignment', 'Unassigned')}",
                f"- Diagnostic Criteria Count: {rotterdam.get('criteria_present_count', 0)} of 3 pillars supported by records",
                f"- Clinical Assessment Summary: {rotterdam.get('clinical_support_summary', 'N/A')}",
            ])
            missing_docs = rotterdam.get("criteria_missing_documentation") or []
            if missing_docs:
                lines.append("- Missing Diagnostic Documentation:")
                for m in missing_docs:
                    lines.append(f"  * {m}")

        # Global missing summary
        if self.missing_data_summary:
            lines.append("\n## 7. Missing Clinical Data Summary")
            for gap in self.missing_data_summary:
                lines.append(f"- {gap}")

        lines.extend([
            "\n---",
            "CRITICAL INSTRUCTION FOR AI REASONING:",
            "- Do not invent values or assume missing tests are normal or abnormal.",
            "- Only refer to findings that appear above.",
            "- When data is insufficient, state that transparently and recommend discussing with a clinician.",
        ])

        return "\n".join(lines)


# ==============================================================================
# Helper Calculation Functions
# ==============================================================================

def _calculate_bmi(height_cm: Optional[float], weight_kg: Optional[float]) -> Tuple[Optional[float], Optional[str]]:
    """Deterministically calculate BMI and standard WHO categorization."""
    if not height_cm or not weight_kg or height_cm <= 0 or weight_kg <= 0:
        return None, None

    height_m = height_cm / 100.0
    bmi = round(weight_kg / (height_m * height_m), 1)

    if bmi < 18.5:
        category = "Underweight"
    elif bmi < 25.0:
        category = "Normal Weight"
    elif bmi < 30.0:
        category = "Overweight"
    elif bmi < 35.0:
        category = "Obesity Class I"
    elif bmi < 40.0:
        category = "Obesity Class II"
    else:
        category = "Obesity Class III"

    return bmi, category


def _format_date(val: Any) -> Optional[str]:
    """Format dates or datetimes to YYYY-MM-DD string."""
    if val is None:
        return None
    if isinstance(val, (datetime, date)):
        return val.strftime("%Y-%m-%d")
    s = str(val).strip()
    return s[:10] if len(s) >= 10 else s


def _format_datetime(val: Any) -> Optional[str]:
    """Format datetime to ISO 8601 UTC string."""
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is None:
            val = val.replace(tzinfo=timezone.utc)
        return val.isoformat()
    return str(val)


# Critical PCOS biomarkers that should be monitored
CRITICAL_PCOS_BIOMARKER_NAMES = [
    "Total Testosterone",
    "Free Testosterone",
    "DHEA-S",
    "Fasting Glucose",
    "HbA1c",
    "Fasting Insulin",
    "LH/FSH Ratio",
    "TSH",
    "25-OH Vitamin D",
]


# ==============================================================================
# Main Context Builder Function
# ==============================================================================

def build_user_health_context(
    db: Session,
    user: User,
    *,
    symptom_days_limit: int = 90,
    lifestyle_days_limit: int = 90,
    cycle_limit: int = 24,
) -> UserHealthContext:
    """Build a comprehensive, strictly isolated health context for the authenticated user.

    Parameters:
    - db: Active SQLAlchemy session.
    - user: Authenticated User model instance verified by security dependencies.
    - symptom_days_limit: Max recent daily symptom records to query (default: 90).
    - lifestyle_days_limit: Max recent lifestyle records to query (default: 90).
    - cycle_limit: Max recent menstrual cycle records to query (default: 24).

    Returns:
    - UserHealthContext containing structured, validated, and de-identified clinical data.
    """
    if not user or not user.id:
        raise UserNotFoundError("Valid authenticated user instance is required.")

    user_id = user.id
    now_utc = datetime.now(timezone.utc)
    today = now_utc.date()

    try:
        # ----------------------------------------------------------------------
        # 1. Health Profile
        # ----------------------------------------------------------------------
        profile_row = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()

        profile_data = HealthProfileData()
        if profile_row:
            bmi, bmi_cat = _calculate_bmi(profile_row.height, profile_row.weight)
            missing_profile_fields = []
            if profile_row.age is None:
                missing_profile_fields.append("age")
            if profile_row.height is None:
                missing_profile_fields.append("height")
            if profile_row.weight is None:
                missing_profile_fields.append("weight")
            if not profile_row.diagnosis_status:
                missing_profile_fields.append("diagnosis_status")

            profile_data = HealthProfileData(
                is_present=True,
                age=profile_row.age,
                height_cm=profile_row.height,
                weight_kg=profile_row.weight,
                calculated_bmi=bmi,
                bmi_category=bmi_cat,
                diagnosis_status=profile_row.diagnosis_status,
                diagnosis_year=profile_row.diagnosis_year,
                existing_conditions=list(profile_row.existing_conditions or []),
                medications=list(profile_row.medications or []),
                last_updated=_format_datetime(profile_row.updated_at or profile_row.created_at),
                missing_fields=missing_profile_fields,
            )
        else:
            profile_data.missing_fields = ["age", "height", "weight", "diagnosis_status"]

        # ----------------------------------------------------------------------
        # 2. Menstrual Cycles
        # ----------------------------------------------------------------------
        cycle_rows = (
            db.query(MenstrualCycle)
            .filter(MenstrualCycle.user_id == user_id)
            .order_by(MenstrualCycle.period_start_date.desc())
            .limit(cycle_limit)
            .all()
        )

        cycle_data = CycleData()
        if cycle_rows:
            cycle_history = []
            for c in cycle_rows:
                cycle_history.append({
                    "id": c.id,
                    "period_start_date": _format_date(c.period_start_date),
                    "period_end_date": _format_date(c.period_end_date),
                    "cycle_length": c.cycle_length,
                    "flow_intensity": c.flow_intensity,
                    "notes": c.notes,
                })

            cycle_stats = calculate_cycle_statistics(cycle_rows)

            latest_cycle_start = cycle_rows[0].period_start_date
            days_since_period = (today - latest_cycle_start).days if latest_cycle_start else None

            cycle_data = CycleData(
                is_present=True,
                total_recorded_cycles=len(cycle_rows),
                latest_cycle_start=_format_date(latest_cycle_start),
                days_since_latest_period=days_since_period,
                history=cycle_history,
                statistics=asdict(cycle_stats),
                missing_data_note=cycle_stats.missing_data_note,
            )
        else:
            cycle_data.missing_data_note = "No menstrual cycles recorded. At least 2 completed cycles are required for rhythm assessment."

        # ----------------------------------------------------------------------
        # 3. Daily Symptoms
        # ----------------------------------------------------------------------
        symptom_rows = (
            db.query(DailySymptom)
            .filter(DailySymptom.user_id == user_id)
            .order_by(DailySymptom.log_date.desc())
            .limit(symptom_days_limit)
            .all()
        )

        symptom_data = SymptomData()
        if symptom_rows:
            recent_symptoms = []
            all_symptom_texts = []
            all_notes_list = []
            fatigue_scores = []
            bloating_scores = []
            pelvic_pain_scores = []
            acne_counts: Dict[str, int] = {}
            hair_loss_counts: Dict[str, int] = {}
            unwanted_hair_counts: Dict[str, int] = {}

            for s in symptom_rows:
                recent_symptoms.append({
                    "id": s.id,
                    "log_date": _format_date(s.log_date),
                    "acne_severity": s.acne_severity,
                    "hair_loss": s.hair_loss,
                    "unwanted_hair_growth": s.unwanted_hair_growth,
                    "fatigue_level": s.fatigue_level,
                    "bloating": s.bloating,
                    "pelvic_pain": s.pelvic_pain,
                    "mood": s.mood,
                    "notes": s.notes,
                })

                if s.fatigue_level is not None:
                    fatigue_scores.append(s.fatigue_level)
                if s.bloating is not None:
                    bloating_scores.append(s.bloating)
                if s.pelvic_pain is not None:
                    pelvic_pain_scores.append(s.pelvic_pain)

                if s.acne_severity:
                    acne_counts[s.acne_severity] = acne_counts.get(s.acne_severity, 0) + 1
                    all_symptom_texts.append(f"acne {s.acne_severity}")
                if s.hair_loss:
                    hair_loss_counts[s.hair_loss] = hair_loss_counts.get(s.hair_loss, 0) + 1
                    all_symptom_texts.append(f"hair loss {s.hair_loss}")
                if s.unwanted_hair_growth:
                    unwanted_hair_counts[s.unwanted_hair_growth] = unwanted_hair_counts.get(s.unwanted_hair_growth, 0) + 1
                    all_symptom_texts.append(f"unwanted hair {s.unwanted_hair_growth}")
                if s.mood:
                    all_symptom_texts.append(s.mood)
                if s.notes:
                    all_notes_list.append(s.notes)

            # Red flag screening
            red_flag_res = screen_urgent_symptoms(
                symptoms=all_symptom_texts,
                notes=" ".join(all_notes_list),
            )

            # Aggregate summary
            symptom_summary = {
                "mean_fatigue": round(sum(fatigue_scores) / len(fatigue_scores), 1) if fatigue_scores else None,
                "mean_bloating": round(sum(bloating_scores) / len(bloating_scores), 1) if bloating_scores else None,
                "mean_pelvic_pain": round(sum(pelvic_pain_scores) / len(pelvic_pain_scores), 1) if pelvic_pain_scores else None,
                "acne_distribution": acne_counts,
                "hair_loss_distribution": hair_loss_counts,
                "unwanted_hair_distribution": unwanted_hair_counts,
            }

            symptom_data = SymptomData(
                is_present=True,
                total_logged_days=len(symptom_rows),
                date_range_start=_format_date(symptom_rows[-1].log_date),
                date_range_end=_format_date(symptom_rows[0].log_date),
                recent_logs=recent_symptoms[:14],  # Most recent 2 weeks of raw logs
                symptom_summary=symptom_summary,
                red_flag_screening=red_flag_res,
            )
        else:
            symptom_data.missing_data_note = "No daily symptoms logged."
            symptom_data.red_flag_screening = screen_urgent_symptoms([], None)

        # ----------------------------------------------------------------------
        # 4. Lifestyle Logs
        # ----------------------------------------------------------------------
        lifestyle_rows = (
            db.query(LifestyleLog)
            .filter(LifestyleLog.user_id == user_id)
            .order_by(LifestyleLog.log_date.desc())
            .limit(lifestyle_days_limit)
            .all()
        )

        lifestyle_data = LifestyleData()
        if lifestyle_rows:
            recent_lifestyle = []
            sleep_list = []
            stress_list = []
            water_list = []
            exercise_list = []

            for l in lifestyle_rows:
                recent_lifestyle.append({
                    "id": l.id,
                    "log_date": _format_date(l.log_date),
                    "sleep_hours": l.sleep_hours,
                    "stress_level": l.stress_level,
                    "water_intake": l.water_intake,
                    "exercise_minutes": l.exercise_minutes,
                    "food_habits": l.food_habits,
                    "meal_regularity": l.meal_regularity,
                })
                sleep_list.append(l.sleep_hours)
                stress_list.append(l.stress_level)
                water_list.append(l.water_intake)
                exercise_list.append(l.exercise_minutes)

            averages = {
                "avg_sleep_hours": round(sum(sleep_list) / len(sleep_list), 1) if sleep_list else None,
                "avg_stress_level": round(sum(stress_list) / len(stress_list), 1) if stress_list else None,
                "avg_water_intake": round(sum(water_list) / len(water_list), 1) if water_list else None,
                "avg_exercise_minutes": round(sum(exercise_list) / len(exercise_list), 1) if exercise_list else None,
            }

            # Statistical Pearson correlations with daily symptoms
            corrs = calculate_symptom_correlations(symptom_rows, lifestyle_rows)
            corr_dicts = [asdict(c) for c in corrs]

            lifestyle_data = LifestyleData(
                is_present=True,
                total_logged_days=len(lifestyle_rows),
                recent_logs=recent_lifestyle[:14],
                averages=averages,
                correlations=corr_dicts,
            )
        else:
            lifestyle_data.missing_data_note = "No lifestyle logs recorded."

        # ----------------------------------------------------------------------
        # 5. Laboratory Reports
        # ----------------------------------------------------------------------
        lab_rows = (
            db.query(LabReport)
            .filter(LabReport.user_id == user_id)
            .order_by(LabReport.report_date.desc())
            .all()
        )

        lab_data = LabReportData()
        if lab_rows:
            evaluated_labs = []
            abnormal_labs = []
            recorded_biomarker_canonicals = set()

            for r in lab_rows:
                ev = evaluate_biomarker(
                    test_name=r.test_name,
                    value=r.test_value,
                    unit=r.unit,
                    lab_normal_range=r.reference_range,
                )
                ev_dict = asdict(ev)
                ev_dict["report_name"] = r.report_name
                ev_dict["report_date"] = _format_date(r.report_date)
                evaluated_labs.append(ev_dict)
                recorded_biomarker_canonicals.add(ev.canonical_name.lower())

                if ev.status != "Normal":
                    abnormal_labs.append(ev_dict)

            missing_critical = [
                name for name in CRITICAL_PCOS_BIOMARKER_NAMES
                if name.lower() not in recorded_biomarker_canonicals
            ]

            lab_data = LabReportData(
                is_present=True,
                total_biomarkers_recorded=len(lab_rows),
                latest_report_date=_format_date(lab_rows[0].report_date),
                evaluated_biomarkers=evaluated_labs,
                abnormal_biomarkers=abnormal_labs,
                missing_critical_pcos_biomarkers=missing_critical,
            )
        else:
            lab_data.missing_data_note = "No laboratory biomarker reports on record."
            lab_data.missing_critical_pcos_biomarkers = list(CRITICAL_PCOS_BIOMARKER_NAMES)

        # ----------------------------------------------------------------------
        # 6. Clinical Records & Educational Rotterdam Assessment
        # ----------------------------------------------------------------------
        clinical_rows = (
            db.query(ClinicalRecord)
            .filter(ClinicalRecord.user_id == user_id)
            .order_by(ClinicalRecord.recorded_at.desc())
            .all()
        )

        clinical_data = ClinicalRecordData()
        if clinical_rows:
            clin_records = []
            for cr in clinical_rows:
                clin_records.append({
                    "id": cr.id,
                    "testosterone": cr.testosterone,
                    "free_testosterone": cr.free_testosterone,
                    "dheas": cr.dheas,
                    "amh": cr.amh,
                    "ultrasound_findings": cr.ultrasound_findings,
                    "ovulation_history": cr.ovulation_history,
                    "recorded_at": _format_datetime(cr.recorded_at),
                })
            clinical_data = ClinicalRecordData(
                is_present=True,
                total_records=len(clinical_rows),
                latest_record_date=_format_datetime(clinical_rows[0].recorded_at),
                records=clin_records,
            )
        else:
            clinical_data.missing_data_note = "No clinical records on record."

        # Educational Rotterdam Assessment combining cycles, labs, symptoms, and clinical records
        rotterdam_res = assess_rotterdam_criteria_educational(
            profile=profile_row,
            cycles=cycle_rows,
            symptoms=symptom_rows,
            lab_reports=lab_rows,
            clinical_records=clinical_rows,
        )
        clinical_data.rotterdam_assessment = asdict(rotterdam_res)

        # ----------------------------------------------------------------------
        # 7. Data Freshness & Global Missing Summary
        # ----------------------------------------------------------------------
        dates_to_compare: List[date] = []
        if profile_row and profile_row.updated_at:
            dates_to_compare.append(profile_row.updated_at.date())
        if cycle_rows and cycle_rows[0].period_start_date:
            dates_to_compare.append(cycle_rows[0].period_start_date)
        if symptom_rows and symptom_rows[0].log_date:
            dates_to_compare.append(symptom_rows[0].log_date)
        if lifestyle_rows and lifestyle_rows[0].log_date:
            dates_to_compare.append(lifestyle_rows[0].log_date)
        if lab_rows and lab_rows[0].report_date:
            dates_to_compare.append(lab_rows[0].report_date)
        if clinical_rows and clinical_rows[0].recorded_at:
            dates_to_compare.append(clinical_rows[0].recorded_at.date())

        most_recent_date = max(dates_to_compare) if dates_to_compare else None
        days_since_activity = (today - most_recent_date).days if most_recent_date else None

        freshness = DataFreshness(
            profile_updated_at=profile_data.last_updated,
            latest_cycle_date=cycle_data.latest_cycle_start,
            latest_symptom_date=_format_date(symptom_rows[0].log_date) if symptom_rows else None,
            latest_lifestyle_date=_format_date(lifestyle_rows[0].log_date) if lifestyle_rows else None,
            latest_lab_date=lab_data.latest_report_date,
            latest_clinical_record_date=clinical_data.latest_record_date,
            most_recent_activity_date=_format_date(most_recent_date),
            days_since_latest_activity=days_since_activity,
        )

        # Global missing summary
        missing_summary: List[str] = []
        if not profile_data.is_present:
            missing_summary.append("Health profile has not been initialized.")
        elif profile_data.missing_fields:
            missing_summary.append(f"Health profile is incomplete (missing: {', '.join(profile_data.missing_fields)}).")

        if not cycle_data.is_present or cycle_data.total_recorded_cycles < 2:
            missing_summary.append("Insufficient menstrual cycle history (minimum 2 cycles needed for regularity classification).")

        if not symptom_data.is_present or symptom_data.total_logged_days < 7:
            missing_summary.append("Insufficient daily symptom logs (at least 7 days needed for lifestyle correlation analysis).")

        if not lab_data.is_present:
            missing_summary.append("No laboratory biomarker reports logged.")
        elif lab_data.missing_critical_pcos_biomarkers:
            missing_summary.append(f"Key unrecorded PCOS biomarkers: {', '.join(lab_data.missing_critical_pcos_biomarkers[:4])}.")

        if not clinical_data.is_present:
            missing_summary.append("No clinical ultrasound or endocrinology examination records on file.")

        logger.info(
            "User health context built successfully for user_id=%d: cycles=%d, symptoms=%d, lifestyle=%d, labs=%d, clinical=%d",
            user_id,
            len(cycle_rows),
            len(symptom_rows),
            len(lifestyle_rows),
            len(lab_rows),
            len(clinical_rows),
        )

        return UserHealthContext(
            user_id=user_id,
            generated_at=_format_datetime(now_utc),
            freshness=freshness,
            profile=profile_data,
            cycles=cycle_data,
            symptoms=symptom_data,
            lifestyle=lifestyle_data,
            labs=lab_data,
            clinical=clinical_data,
            missing_data_summary=missing_summary,
        )

    except SQLAlchemyError as exc:
        logger.error("Database query failed while building user health context for user_id=%d: %s", user_id, type(exc).__name__)
        raise ContextBuilderDatabaseError("Failed to query user health context due to a database error.") from exc
    except Exception as exc:
        if isinstance(exc, ContextBuilderError):
            raise
        logger.error("Unexpected error in build_user_health_context for user_id=%d: %s", user_id, type(exc).__name__)
        raise ContextBuilderError(f"Context building failed: {exc}") from exc


def build_user_health_context_by_id(
    db: Session,
    user_id: int,
    *,
    symptom_days_limit: int = 90,
    lifestyle_days_limit: int = 90,
    cycle_limit: int = 24,
) -> UserHealthContext:
    """Convenience lookup when user_id is provided from a verified internal backend service."""
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError("Invalid user_id provided.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise UserNotFoundError(f"User with ID {user_id} does not exist.")

    return build_user_health_context(
        db=db,
        user=user,
        symptom_days_limit=symptom_days_limit,
        lifestyle_days_limit=lifestyle_days_limit,
        cycle_limit=cycle_limit,
    )
