"""PCOSCOPE Health Intelligence & Pattern Discovery Engine.

Transforms authentic patient health records from PostgreSQL into actionable,
evidence-grounded clinical intelligence.

CORE CAPABILITIES:
1. Menstrual Cycle Rhythm & Variance Analysis (Monash 2023 guideline thresholds).
   - Strict labeling of estimated cycle phases; never claims confirmed ovulation.
2. Temporal Symptom Clustering & Progression (Rolling 7d, 30d, 90d windows).
   - Co-occurrence frequency, prevalence %, severity tracking.
3. Lifestyle-Symptom Correlation Matrix (Pearson r).
   - Treats N >= 7 as a minimum data-quality threshold, NOT a guarantee of statistical significance.
   - Refuses to assert correlations when N < 7, returning explicit data-quality warnings.
4. Laboratory Biomarker Trajectory & Longitudinal Trends.
   - Chronological tracking of glycemic, androgenic, lipid, and endocrine panels.
5. Evidence-Based Clinical Care Gaps.
   - Gaps mapped against Monash 2023, Endocrine Society 2013, and Rotterdam 2004 criteria.
6. Objective Record Completeness & Data Quality Scoring (0-100%).
7. AI-Assisted Narrative Synthesis Grounded in Real Patient Context.

SAFETY & COMPLIANCE:
- Strict User Isolation: Every query enforces user_id filter.
- Anti-Fabrication: Never injects sample data or synthetic records.
- Clear separation between calculated metrics, statistical associations, and AI narrative interpretations.
"""

from collections import Counter, defaultdict
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union

from sqlalchemy.orm import Session

from app.core.medical_knowledge import DEFAULT_BIOMARKER_RANGES, RotterdamPillar
from app.models.clinical_record import ClinicalRecord
from app.models.daily_symptom import DailySymptom
from app.models.health_profile import HealthProfile
from app.models.lab_report import LabReport
from app.models.lifestyle_log import LifestyleLog
from app.models.menstrual_cycle import MenstrualCycle
from app.models.user import User
from app.schemas.pcoscope import (
    BiomarkerTrajectoryItem,
    CareGapItem,
    CyclePatternMetrics,
    DataCompletenessSummary,
    LifestyleCorrelationItem,
    PcoscopeAnalysisResponse,
    PcoscopeInsightsResponse,
    SymptomClusterItem,
    SymptomTrendsAnalysis,
)
from app.services.ai_engine import (
    AIEngineError,
    _dispatch_ai_request,
)
from app.services.clinical_calculator import (
    assess_rotterdam_criteria_educational,
    calculate_cycle_statistics,
    calculate_pearson_correlation,
    evaluate_biomarker,
    screen_urgent_symptoms,
)
from app.services.context_builder import UserHealthContext, build_user_health_context

logger = logging.getLogger("pcos360.pcoscope_engine")

STANDARD_DISCLAIMER = (
    "Educational medical decision-support only. Deterministic calculations, statistical correlations, and pattern "
    "discoveries are provided for informed discussions with licensed healthcare providers and do not constitute an "
    "automated medical diagnosis or prescription."
)

OVULATION_UNCONFIRMED_NOTE = (
    "UNCONFIRMED: Calendar estimation only. True clinical ovulation confirmation requires mid-luteal serum progesterone "
    "(>= 3 ng/mL), serial basal body temperature biphasic shift, or pelvic ultrasound follicular tracking."
)


# ==============================================================================
# 1. Menstrual Cycle Pattern Analysis
# ==============================================================================

def analyze_cycle_patterns(cycles: List[MenstrualCycle]) -> CyclePatternMetrics:
    """Analyze menstrual rhythm, variance, and estimated phase from authentic cycle records."""
    if not cycles:
        return CyclePatternMetrics(
            sample_size=0,
            has_sufficient_data=False,
            mean_length_days=None,
            median_length_days=None,
            stdev_days=None,
            min_length_days=None,
            max_length_days=None,
            rhythm_classification="No Cycles Logged",
            is_irregular=False,
            current_cycle_day=None,
            estimated_current_phase="No Menstrual Cycles Logged",
            ovulation_confirmation_status=OVULATION_UNCONFIRMED_NOTE,
            next_period_estimated=None,
            trend_direction="Insufficient Data",
            clinical_interpretation="No menstrual cycles have been recorded yet. Tracking at least 3 consecutive cycles is required to evaluate rhythm and regularity.",
        )

    # Sort cycles chronologically by period_start_date ASC
    sorted_cycles = sorted(cycles, key=lambda c: c.period_start_date)
    lengths = [c.cycle_length for c in sorted_cycles if c.cycle_length and c.cycle_length > 0]
    stats = calculate_cycle_statistics(sorted_cycles)

    latest_cycle = sorted_cycles[-1]
    today = date.today()
    days_elapsed = (today - latest_cycle.period_start_date).days + 1
    current_cycle_day = max(1, days_elapsed)

    mean_len = stats.mean_length or float(latest_cycle.cycle_length or 28)
    expected_cycle_len = max(21, round(mean_len))

    # Calculate estimated phase strictly labeled as ESTIMATED
    estimated_ovulation_day = max(8, expected_cycle_len - 14)
    if current_cycle_day <= 5:
        estimated_phase = f"Estimated Menstrual Phase (Day {current_cycle_day})"
    elif current_cycle_day < (estimated_ovulation_day - 2):
        estimated_phase = f"Estimated Early-to-Mid Follicular Phase (Day {current_cycle_day})"
    elif (estimated_ovulation_day - 2) <= current_cycle_day <= (estimated_ovulation_day + 2):
        estimated_phase = f"Estimated Periovulatory Window (Day {current_cycle_day} - Calendar estimation only, unconfirmed)"
    elif (estimated_ovulation_day + 2) < current_cycle_day <= expected_cycle_len:
        estimated_phase = f"Estimated Luteal Phase (Day {current_cycle_day})"
    else:
        estimated_phase = f"Estimated Extended / Delayed Cycle (Day {current_cycle_day} - Exceeds expected {expected_cycle_len}d duration)"

    # Estimated next period date
    next_period_date = latest_cycle.period_start_date + timedelta(days=expected_cycle_len)
    next_period_estimated = next_period_date.isoformat()

    # Determine trend direction across consecutive cycles
    trend_direction = "Stable"
    if len(lengths) >= 3:
        diffs = [lengths[i] - lengths[i - 1] for i in range(1, len(lengths))]
        avg_diff = sum(diffs) / len(diffs)
        if stats.stdev_length and stats.stdev_length >= 7.0:
            trend_direction = "Highly Variable"
        elif avg_diff >= 3.0:
            trend_direction = "Lengthening"
        elif avg_diff <= -3.0:
            trend_direction = "Shortening"
        else:
            trend_direction = "Stable"
    elif len(lengths) < 3:
        trend_direction = "Insufficient Data"

    return CyclePatternMetrics(
        sample_size=stats.sample_size,
        has_sufficient_data=stats.has_sufficient_data,
        mean_length_days=stats.mean_length,
        median_length_days=stats.median_length,
        stdev_days=stats.stdev_length,
        min_length_days=stats.min_length,
        max_length_days=stats.max_length,
        rhythm_classification=stats.rhythm_classification,
        is_irregular=stats.is_irregular,
        current_cycle_day=current_cycle_day,
        estimated_current_phase=estimated_phase,
        ovulation_confirmation_status=OVULATION_UNCONFIRMED_NOTE,
        next_period_estimated=next_period_estimated,
        trend_direction=trend_direction,
        clinical_interpretation=stats.clinical_interpretation,
    )


# ==============================================================================
# 2. Symptom Cluster & Frequency Analysis
# ==============================================================================

def _map_severity_to_score(val: Any) -> float:
    """Map categorical or numeric symptom severity to a standardized 0-10 scale."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(max(0.0, min(10.0, float(val))))
    text = str(val).strip().lower()
    if text == "severe":
        return 9.0
    if text == "moderate":
        return 6.0
    if text == "mild":
        return 3.0
    if text in ("none", "absent", "0"):
        return 0.0
    return 3.0  # default mild presence if positive string


def analyze_symptom_trends(
    symptoms: List[DailySymptom],
    lifestyle_logs: List[LifestyleLog],
    window_days: int = 30,
) -> SymptomTrendsAnalysis:
    """Aggregate symptom frequencies, severity averages, and co-occurrences within a rolling window."""
    if not symptoms:
        return SymptomTrendsAnalysis(
            window_days=window_days,
            total_logged_days=0,
            top_clusters=[],
            temporal_timeline=[],
            summary_note="No daily symptoms logged yet. Regular check-ins help uncover hormonal patterns and symptom clustering.",
        )

    # Filter to symptoms within window_days from the latest log date
    sorted_symptoms = sorted(symptoms, key=lambda s: s.log_date)
    latest_date = sorted_symptoms[-1].log_date
    cutoff_date = latest_date - timedelta(days=window_days)
    window_symptoms = [s for s in sorted_symptoms if s.log_date >= cutoff_date]

    total_days = len(window_symptoms)
    if total_days == 0:
        window_symptoms = sorted_symptoms[-min(len(sorted_symptoms), window_days):]
        total_days = len(window_symptoms)

    # Symptom field definitions
    symptom_keys = [
        ("fatigue_level", "Fatigue", "fatigue"),
        ("acne_severity", "Acne", "acne"),
        ("bloating", "Bloating", "bloating"),
        ("pelvic_pain", "Pelvic Pain", "pelvic_pain"),
        ("hair_loss", "Hair Thinning", "hair_loss"),
        ("unwanted_hair_growth", "Hirsutism", "unwanted_hair_growth"),
    ]

    # Map lifestyle logs by date for charting
    lifestyle_by_date = {l.log_date: l for l in lifestyle_logs}

    # Aggregate occurrence and co-occurrence
    symptom_counts: Dict[str, int] = defaultdict(int)
    symptom_severities: Dict[str, List[float]] = defaultdict(list)
    date_active_symptoms: Dict[date, List[str]] = defaultdict(list)

    timeline_points: List[Dict[str, Any]] = []

    for s in window_symptoms:
        d = s.log_date
        active_on_day = []
        point_data: Dict[str, Any] = {"date": d.isoformat()}

        for attr, label, canonical in symptom_keys:
            raw_val = getattr(s, attr, None)
            score = _map_severity_to_score(raw_val)
            point_data[canonical] = score

            if score > 0:
                symptom_counts[canonical] += 1
                symptom_severities[canonical].append(score)
                active_on_day.append(label)

        # Attach lifestyle values for time series if present
        life = lifestyle_by_date.get(d)
        if life:
            point_data["sleep_hours"] = life.sleep_hours
            point_data["stress_level"] = life.stress_level
            point_data["exercise_minutes"] = life.exercise_minutes
            point_data["water_intake"] = life.water_intake

        date_active_symptoms[d] = active_on_day
        timeline_points.append(point_data)

    # Build co-occurrence map
    co_occurrences: Dict[str, Counter] = defaultdict(Counter)
    for d, sym_list in date_active_symptoms.items():
        for i, sym_a in enumerate(sym_list):
            for sym_b in sym_list[i + 1:]:
                co_occurrences[sym_a][sym_b] += 1
                co_occurrences[sym_b][sym_a] += 1

    # Build cluster items
    clusters: List[SymptomClusterItem] = []
    half_index = max(1, total_days // 2)

    for attr, label, canonical in symptom_keys:
        cnt = symptom_counts.get(canonical, 0)
        if cnt == 0:
            continue

        scores = symptom_severities.get(canonical, [])
        avg_score = round(sum(scores) / len(scores), 1) if scores else 0.0
        prev_pct = round((cnt / total_days) * 100, 1)

        # Trend direction (first half vs second half)
        earlier_scores = [
            _map_severity_to_score(getattr(s, attr, None))
            for s in window_symptoms[:half_index]
            if _map_severity_to_score(getattr(s, attr, None)) > 0
        ]
        later_scores = [
            _map_severity_to_score(getattr(s, attr, None))
            for s in window_symptoms[half_index:]
            if _map_severity_to_score(getattr(s, attr, None)) > 0
        ]

        if earlier_scores and later_scores:
            diff = (sum(later_scores) / len(later_scores)) - (sum(earlier_scores) / len(earlier_scores))
            if diff >= 1.0:
                trend = "Increasing"
            elif diff <= -1.0:
                trend = "Decreasing"
            else:
                trend = "Stable"
        else:
            trend = "Stable" if cnt >= 3 else "Insufficient Data"

        # Severity label
        if avg_score >= 7.0:
            sev_label = "Severe"
        elif avg_score >= 4.0:
            sev_label = "Moderate"
        else:
            sev_label = "Mild"

        top_co = [name for name, _ in co_occurrences.get(label, Counter()).most_common(3)]

        clusters.append(
            SymptomClusterItem(
                symptom_key=canonical,
                display_name=label,
                occurrences_count=cnt,
                total_window_days=total_days,
                prevalence_pct=prev_pct,
                average_severity=avg_score,
                severity_label=sev_label,
                trend_direction=trend,
                co_occurring_symptoms=top_co,
            )
        )

    # Sort clusters by prevalence descending
    clusters.sort(key=lambda c: (c.prevalence_pct, c.average_severity), reverse=True)

    summary_note = (
        f"Analyzed {total_days} daily symptom logs over rolling {window_days} days. "
        + (f"Most prominent symptom is {clusters[0].display_name} ({clusters[0].prevalence_pct}% prevalence)." if clusters else "No symptoms were reported above baseline.")
    )

    return SymptomTrendsAnalysis(
        window_days=window_days,
        total_logged_days=total_days,
        top_clusters=clusters,
        temporal_timeline=timeline_points,
        summary_note=summary_note,
    )


# ==============================================================================
# 3. Lifestyle-Symptom Correlation Matrix
# ==============================================================================

def analyze_lifestyle_correlations(
    symptoms: List[DailySymptom],
    lifestyle_logs: List[LifestyleLog],
    min_sample_size: int = 7,
) -> List[LifestyleCorrelationItem]:
    """Compute Pearson correlations between daily lifestyle habits and symptoms.

    REQUIREMENT: Treat N >= 7 as a minimum data-quality threshold, NOT a guarantee of statistical significance.
    If N < 7, refuses to assert correlation and returns explicit data-quality warning.
    """
    results: List[LifestyleCorrelationItem] = []

    # Map by exact date
    sym_by_date: Dict[date, DailySymptom] = {s.log_date: s for s in symptoms}
    life_by_date: Dict[date, LifestyleLog] = {l.log_date: l for l in lifestyle_logs}

    paired_dates = sorted(set(sym_by_date.keys()).intersection(set(life_by_date.keys())))
    n_paired = len(paired_dates)

    # Pairs to evaluate
    pair_definitions = [
        (
            "Sleep Duration (hours)",
            "Fatigue Severity (1-10)",
            lambda l: l.sleep_hours,
            lambda s: float(s.fatigue_level) if s.fatigue_level is not None else None,
            "Negative",
            "Higher sleep duration correlates with lower reported fatigue levels.",
            "Shorter sleep duration correlates with elevated fatigue scores.",
        ),
        (
            "Reported Stress Level (1-5)",
            "Acne Severity (Score 0-9)",
            lambda l: float(l.stress_level),
            lambda s: _map_severity_to_score(s.acne_severity) if s.acne_severity else None,
            "Positive",
            "Elevated stress levels correlate with heightened acne severity scores.",
            "Lower stress levels correlate with calmer skin reports.",
        ),
        (
            "Physical Activity (minutes)",
            "Bloating Severity (1-10)",
            lambda l: float(l.exercise_minutes),
            lambda s: float(s.bloating) if s.bloating is not None else None,
            "Negative",
            "Greater daily physical activity correlates with reduced subjective bloating.",
            "Lower physical activity days correlate with increased bloating.",
        ),
        (
            "Daily Hydration (liters)",
            "Fatigue Severity (1-10)",
            lambda l: float(l.water_intake),
            lambda s: float(s.fatigue_level) if s.fatigue_level is not None else None,
            "Negative",
            "Higher water intake correlates with lower reported fatigue.",
            "Low hydration days correlate with increased fatigue.",
        ),
        (
            "Sleep Duration (hours)",
            "Stress Level (1-5)",
            lambda l: l.sleep_hours,
            lambda l_s: float(l_s.stress_level),  # paired with lifestyle stress
            "Negative",
            "Adequate sleep hours correlate with lower subjective daytime stress.",
            "Sleep restriction correlates with heightened stress reports.",
        ),
    ]

    for factor_a, factor_b, get_x, get_y, expected_dir, interp_pos, interp_neg in pair_definitions:
        x_vals: List[float] = []
        y_vals: List[float] = []

        for d in paired_dates:
            s_obj = sym_by_date[d]
            l_obj = life_by_date[d]

            val_x = get_x(l_obj)
            val_y = get_y(l_obj) if factor_b == "Stress Level (1-5)" else get_y(s_obj)

            if val_x is not None and val_y is not None:
                x_vals.append(float(val_x))
                y_vals.append(float(val_y))

        current_n = len(x_vals)

        if current_n < min_sample_size:
            # Below minimum data quality threshold
            results.append(
                LifestyleCorrelationItem(
                    factor_a=factor_a,
                    factor_b=factor_b,
                    sample_size=current_n,
                    has_sufficient_data=False,
                    correlation_coefficient=None,
                    direction=None,
                    strength=None,
                    data_quality_status=f"Insufficient sample size (N={current_n} < {min_sample_size})",
                    significance_warning=(
                        f"Data-quality threshold not met (N={current_n} < {min_sample_size} paired daily logs). "
                        f"A minimum of {min_sample_size} paired check-ins is required to observe preliminary associations."
                    ),
                    interpretation=(
                        f"Only {current_n} of the required {min_sample_size} paired daily check-ins are logged. "
                        f"Continue daily symptom and lifestyle check-ins to unlock statistical pattern discovery."
                    ),
                )
            )
        else:
            # Meets N >= 7 threshold
            r_val = calculate_pearson_correlation(x_vals, y_vals)
            if r_val is None:
                results.append(
                    LifestyleCorrelationItem(
                        factor_a=factor_a,
                        factor_b=factor_b,
                        sample_size=current_n,
                        has_sufficient_data=True,
                        correlation_coefficient=None,
                        direction="None",
                        strength="None",
                        data_quality_status=f"Sufficient preliminary data (N={current_n} >= {min_sample_size})",
                        significance_warning=(
                            f"Sample size (N={current_n}) meets the minimum preliminary data-quality threshold (N>={min_sample_size}). "
                            "However, zero variance was detected in one or both variables, preventing mathematical correlation."
                        ),
                        interpretation=f"No variation observed in {factor_a} or {factor_b} across {current_n} days.",
                    )
                )
            else:
                r_rounded = round(r_val, 2)
                direction = "Positive" if r_rounded > 0.1 else ("Negative" if r_rounded < -0.1 else "None")
                abs_r = abs(r_rounded)
                strength = "Strong" if abs_r >= 0.7 else ("Moderate" if abs_r >= 0.4 else "Weak")

                if direction == "Positive":
                    interp = f"Observed a {strength.lower()} positive association (r = {r_rounded:+.2f}). {interp_pos}"
                elif direction == "Negative":
                    interp = f"Observed a {strength.lower()} inverse association (r = {r_rounded:+.2f}). {interp_neg}"
                else:
                    interp = f"No meaningful statistical correlation observed between {factor_a} and {factor_b} (r = {r_rounded:+.2f})."

                results.append(
                    LifestyleCorrelationItem(
                        factor_a=factor_a,
                        factor_b=factor_b,
                        sample_size=current_n,
                        has_sufficient_data=True,
                        correlation_coefficient=r_rounded,
                        direction=direction,
                        strength=strength,
                        data_quality_status=f"Sufficient preliminary data (N={current_n} >= {min_sample_size})",
                        significance_warning=(
                            f"Sample size (N={current_n}) meets the minimum preliminary data-quality threshold (N>={min_sample_size}). "
                            "Note: Observational correlation does NOT establish medical causation or clinical statistical significance. "
                            "Confounding variables such as menstrual cycle phase, dietary glycemic index, and medications must be evaluated clinically."
                        ),
                        interpretation=interp,
                    )
                )

    return results


# ==============================================================================
# 4. Biomarker Trajectory & Longitudinal Trends
# ==============================================================================

def analyze_biomarker_trajectories(lab_reports: List[LabReport]) -> List[BiomarkerTrajectoryItem]:
    """Trace historical biomarker values chronologically across sequential lab reports."""
    if not lab_reports:
        return []

    # Standardize canonical names
    canonical_alias_map = {
        "fasting blood sugar": "fasting_glucose",
        "fasting glucose": "fasting_glucose",
        "glucose": "fasting_glucose",
        "fbs": "fasting_glucose",
        "hba1c": "hba1c",
        "glycated hemoglobin": "hba1c",
        "total testosterone": "total_testosterone",
        "testosterone": "total_testosterone",
        "free testosterone": "free_testosterone",
        "free androgen index": "free_androgen_index",
        "fai": "free_androgen_index",
        "dheas": "dheas",
        "dhea-s": "dheas",
        "dhea sulfate": "dheas",
        "lh": "lh",
        "luteinizing hormone": "lh",
        "fsh": "fsh",
        "follicle stimulating hormone": "fsh",
        "lh:fsh ratio": "lh_fsh_ratio",
        "fasting insulin": "fasting_insulin",
        "insulin": "fasting_insulin",
        "homa-ir": "homa_ir",
        "tsh": "tsh",
        "thyroid stimulating hormone": "tsh",
        "prolactin": "prolactin",
        "lipid ldl": "lipid_ldl",
        "ldl": "lipid_ldl",
        "lipid hdl": "lipid_hdl",
        "hdl": "lipid_hdl",
        "triglycerides": "lipid_triglycerides",
        "total cholesterol": "lipid_total_cholesterol",
        "vitamin d": "vitamin_d",
        "25-hydroxy vitamin d": "vitamin_d",
    }

    # Group reports by canonical biomarker
    grouped: Dict[str, List[LabReport]] = defaultdict(list)
    for r in lab_reports:
        clean_name = r.test_name.strip().lower()
        canonical = canonical_alias_map.get(clean_name, clean_name.replace(" ", "_"))
        grouped[canonical].append(r)

    results: List[BiomarkerTrajectoryItem] = []

    for canonical, records in grouped.items():
        # Sort chronologically ASC
        sorted_records = sorted(records, key=lambda x: (x.report_date, x.id))
        history_points: List[Dict[str, Any]] = []

        for rec in sorted_records:
            eval_res = evaluate_biomarker(
                test_name=rec.test_name,
                value=rec.test_value,
                unit=rec.unit,
                lab_normal_range=rec.reference_range,
            )
            history_points.append({
                "date": rec.report_date.isoformat(),
                "value": rec.test_value,
                "unit": rec.unit,
                "status": eval_res.status,
                "reference_range": eval_res.reference_interval_applied,
            })

        latest_rec = sorted_records[-1]
        latest_eval = evaluate_biomarker(
            test_name=latest_rec.test_name,
            value=latest_rec.test_value,
            unit=latest_rec.unit,
            lab_normal_range=latest_rec.reference_range,
        )

        # Determine trajectory trend
        trend = "Single Data Point"
        if len(sorted_records) >= 2:
            prev_val = sorted_records[-2].test_value
            curr_val = latest_rec.test_value

            # For tests where lower is generally favorable (glycemic, androgenic, ldl)
            lower_is_better = canonical in {
                "fasting_glucose", "hba1c", "total_testosterone", "free_testosterone",
                "dheas", "fasting_insulin", "homa_ir", "lipid_ldl", "lipid_triglycerides",
            }
            # For tests where higher is favorable (vitamin d, hdl)
            higher_is_better = canonical in {"vitamin_d", "lipid_hdl"}

            diff_pct = ((curr_val - prev_val) / prev_val) * 100 if prev_val > 0 else 0.0

            if abs(diff_pct) < 5.0:
                trend = "Stable"
            elif lower_is_better:
                trend = "Improving" if curr_val < prev_val else "Worsening"
            elif higher_is_better:
                trend = "Improving" if curr_val > prev_val else "Worsening"
            else:
                trend = "Improving" if latest_eval.status == "Normal" else "Stable"

        results.append(
            BiomarkerTrajectoryItem(
                biomarker_name=latest_rec.test_name,
                canonical_name=canonical,
                datapoints_count=len(sorted_records),
                latest_value=latest_rec.test_value,
                latest_unit=latest_rec.unit,
                latest_status=latest_eval.status,
                latest_date=latest_rec.report_date.isoformat(),
                reference_interval=latest_eval.reference_interval_applied,
                trajectory_trend=trend,
                history=history_points,
                clinical_significance=latest_eval.clinical_significance,
            )
        )

    # Sort so abnormal/elevated biomarkers appear first
    results.sort(
        key=lambda b: (
            0 if b.latest_status in ("Elevated", "Low", "Borderline / Impaired") else 1,
            b.biomarker_name,
        )
    )
    return results


# ==============================================================================
# 5. Clinical Care Gaps & Record Completeness
# ==============================================================================

def evaluate_care_gaps(
    profile: Optional[HealthProfile],
    cycles: List[MenstrualCycle],
    symptoms: List[DailySymptom],
    lifestyle_logs: List[LifestyleLog],
    lab_reports: List[LabReport],
    clinical_records: List[ClinicalRecord],
) -> List[CareGapItem]:
    """Identify missing evidence-based evaluations based on Monash 2023 and Endocrine Society guidelines."""
    gaps: List[CareGapItem] = []

    # 1. Profile initialization
    if not profile or not profile.age or not profile.height or not profile.weight:
        gaps.append(
            CareGapItem(
                category="Clinical Profile",
                title="Complete Baseline Biometrics & Health Profile",
                description="Recording age, height, and weight is essential to calculate baseline BMI and tailor metabolic recommendations.",
                priority="High",
                guideline_source="Monash 2023 International PCOS Guideline (Section 3: Lifestyle)",
            )
        )

    # 2. Menstrual cycle tracking
    if len(cycles) < 3:
        gaps.append(
            CareGapItem(
                category="Cycle Tracking",
                title=f"Log Consecutive Menstrual Cycles ({len(cycles)}/3 Logged)",
                description="A minimum of 3 consecutive cycles is required to clinically assess ovulatory regularity and cycle length variability.",
                priority="High" if len(cycles) == 0 else "Medium",
                guideline_source="Monash 2023 & Rotterdam 2004 Ovulatory Dysfunction Criteria",
            )
        )

    # 3. Glycemic Screening (Metabolic Pillar)
    has_glycemic = any(
        "glucose" in r.test_name.lower() or "hba1c" in r.test_name.lower() or "insulin" in r.test_name.lower()
        for r in lab_reports
    )
    if not has_glycemic:
        gaps.append(
            CareGapItem(
                category="Laboratory",
                title="Baseline Glycemic & Insulin Resistance Assessment",
                description="International guidelines recommend screening all women with suspected or diagnosed PCOS for insulin resistance via Fasting Blood Glucose, HbA1c, or OGTT.",
                priority="High",
                guideline_source="Monash 2023 & ADA Guidelines (Metabolic Screening in PCOS)",
            )
        )

    # 4. Biochemical Hyperandrogenism Panel
    has_androgen = any(
        "testosterone" in r.test_name.lower() or "dhea" in r.test_name.lower() or "fai" in r.test_name.lower()
        for r in lab_reports
    )
    if not has_androgen:
        gaps.append(
            CareGapItem(
                category="Laboratory",
                title="Comprehensive Androgen Laboratory Panel",
                description="Testing Total Testosterone, Free Androgen Index (FAI), or DHEA-S is recommended to evaluate biochemical hyperandrogenism.",
                priority="High",
                guideline_source="Monash 2023 Rotterdam Pillar 1 (Biochemical Hyperandrogenism)",
            )
        )

    # 5. Daily Symptom Check-ins
    if len(symptoms) < 7:
        gaps.append(
            CareGapItem(
                category="Daily Symptoms",
                title=f"Log Daily Symptoms to Meet Data-Quality Threshold ({len(symptoms)}/7 Days)",
                description="A minimum of 7 daily logs is required to compute reliable statistical associations between lifestyle habits and symptoms.",
                priority="Medium",
                guideline_source="PCOS360 Statistical Data-Quality Guard (N >= 7)",
            )
        )

    # 6. Lipid & Cardiovascular Risk Panel
    has_lipid = any(
        "lipid" in r.test_name.lower() or "cholesterol" in r.test_name.lower() or "triglyceride" in r.test_name.lower()
        for r in lab_reports
    )
    if not has_lipid:
        gaps.append(
            CareGapItem(
                category="Laboratory",
                title="Lipid Profile & Cardiovascular Risk Assessment",
                description="Fasting lipid profile (Total Cholesterol, HDL, LDL, Triglycerides) is recommended to screen for dyslipidemia associated with PCOS.",
                priority="Low",
                guideline_source="Endocrine Society 2013 PCOS Clinical Practice Guideline",
            )
        )

    return gaps


def calculate_data_completeness(
    profile: Optional[HealthProfile],
    cycles: List[MenstrualCycle],
    symptoms: List[DailySymptom],
    lifestyle_logs: List[LifestyleLog],
    lab_reports: List[LabReport],
) -> DataCompletenessSummary:
    """Calculate an objective profile maturity score (0-100%) based on PostgreSQL records."""
    score = 0
    missing_critical: List[str] = []

    # 1. Profile (20 pts)
    profile_initialized = bool(profile and profile.age and profile.height and profile.weight)
    if profile_initialized:
        score += 20
    else:
        missing_critical.append("Baseline Health Profile (Age, Height, Weight)")

    # 2. Cycles (25 pts)
    cycles_count = len(cycles)
    if cycles_count >= 3:
        score += 25
    elif cycles_count >= 1:
        score += 10
        missing_critical.append("At least 3 consecutive cycle records")
    else:
        missing_critical.append("Menstrual cycle tracking")

    # 3. Symptoms (20 pts)
    symptoms_days = len({s.log_date for s in symptoms})
    if symptoms_days >= 7:
        score += 20
    elif symptoms_days >= 1:
        score += 10
        missing_critical.append("Minimum 7 days of daily symptom tracking")
    else:
        missing_critical.append("Daily symptom logging")

    # 4. Lifestyle (15 pts)
    lifestyle_days = len({l.log_date for l in lifestyle_logs})
    if lifestyle_days >= 7:
        score += 15
    elif lifestyle_days >= 1:
        score += 8
        missing_critical.append("Minimum 7 days of lifestyle logging")
    else:
        missing_critical.append("Daily lifestyle habits logging")

    # 5. Labs (20 pts)
    labs_count = len(lab_reports)
    if labs_count >= 2:
        score += 20
    elif labs_count == 1:
        score += 10
        missing_critical.append("Comprehensive laboratory biomarker panel")
    else:
        missing_critical.append("Laboratory blood tests")

    # Actionable recommendation
    if not profile_initialized:
        rec = "Start by completing your health profile with height and weight to establish baseline biometrics."
    elif cycles_count < 3:
        rec = "Log your recent menstrual period dates to evaluate cycle length rhythm and regularity."
    elif symptoms_days < 7 or lifestyle_days < 7:
        rec = "Log daily symptom and lifestyle check-ins for 7 days to unlock statistical correlation insights."
    elif labs_count == 0:
        rec = "Upload baseline metabolic and hormone lab reports (fasting glucose, testosterone) to unlock biomarker trajectories."
    else:
        rec = "Your health profile is comprehensive. Continue consistent daily check-ins to monitor long-term trends."

    return DataCompletenessSummary(
        overall_score_pct=score,
        profile_initialized=profile_initialized,
        cycles_logged_count=cycles_count,
        symptoms_logged_days=symptoms_days,
        lifestyle_logged_days=lifestyle_days,
        lab_biomarkers_count=labs_count,
        missing_critical_elements=missing_critical,
        recommendation=rec,
    )


# ==============================================================================
# 6. PCOSCOPE Analysis Orchestration
# ==============================================================================

def run_pcoscope_analysis(
    db: Session,
    user: User,
    window_days: int = 30,
) -> PcoscopeAnalysisResponse:
    """Run complete deterministic pattern discovery on the authenticated user's records.

    Strictly uses authentic PostgreSQL data. No demo or synthetic data fallback.
    """
    user_id = user.id

    # Retrieve authentic user records with strict user isolation
    profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
    cycles = db.query(MenstrualCycle).filter(MenstrualCycle.user_id == user_id).all()
    symptoms = db.query(DailySymptom).filter(DailySymptom.user_id == user_id).all()
    lifestyle = db.query(LifestyleLog).filter(LifestyleLog.user_id == user_id).all()
    labs = db.query(LabReport).filter(LabReport.user_id == user_id).all()
    clinical = db.query(ClinicalRecord).filter(ClinicalRecord.user_id == user_id).all()

    # 1. Deterministic Cycle Patterns
    cycle_patterns = analyze_cycle_patterns(cycles)

    # 2. Symptom Trends & Clustering
    symptom_trends = analyze_symptom_trends(symptoms=symptoms, lifestyle_logs=lifestyle, window_days=window_days)

    # 3. Lifestyle-Symptom Correlations with N >= 7 guard
    correlations = analyze_lifestyle_correlations(symptoms=symptoms, lifestyle_logs=lifestyle, min_sample_size=7)

    # 4. Biomarker Trajectories
    biomarker_trajectories = analyze_biomarker_trajectories(labs)

    # 5. Clinical Care Gaps
    care_gaps = evaluate_care_gaps(
        profile=profile,
        cycles=cycles,
        symptoms=symptoms,
        lifestyle_logs=lifestyle,
        lab_reports=labs,
        clinical_records=clinical,
    )

    # 6. Data Completeness
    completeness = calculate_data_completeness(
        profile=profile,
        cycles=cycles,
        symptoms=symptoms,
        lifestyle_logs=lifestyle,
        lab_reports=labs,
    )

    # 7. Red Flag Screening on recent symptoms
    recent_symptom_texts = []
    for s in symptoms[-10:]:
        if s.notes:
            recent_symptom_texts.append(s.notes)
    red_flag_res = screen_urgent_symptoms(symptoms=recent_symptom_texts, notes=None)

    # 8. Educational Rotterdam Assessment calculated directly from authentic records
    rotterdam_calc = assess_rotterdam_criteria_educational(
        profile=profile,
        cycles=cycles,
        symptoms=symptoms,
        lab_reports=labs,
        clinical_records=clinical,
    )
    rotterdam_assessment = asdict(rotterdam_calc)

    return PcoscopeAnalysisResponse(
        user_id=user_id,
        analysis_timestamp=datetime.now(timezone.utc).isoformat(),
        data_completeness=completeness,
        cycle_patterns=cycle_patterns,
        symptom_trends=symptom_trends,
        lifestyle_correlations=correlations,
        biomarker_trajectories=biomarker_trajectories,
        care_gaps=care_gaps,
        rotterdam_assessment=rotterdam_assessment,
        urgent_red_flags=red_flag_res,
        disclaimer=STANDARD_DISCLAIMER,
    )


# ==============================================================================
# 7. PCOSCOPE Insights Synthesis (AI Narrative + Deterministic Fallback)
# ==============================================================================

def generate_pcoscope_insights(
    db: Session,
    user: User,
    window_days: int = 30,
) -> PcoscopeInsightsResponse:
    """Generate comprehensive PCOSCOPE insights synthesizing deterministic patterns with AI reasoning."""
    # 1. Run deterministic pattern discovery
    analysis = run_pcoscope_analysis(db=db, user=user, window_days=window_days)

    # 2. Build structured clinical prompt
    prompt_lines = [
        "# PATIENT PCOSCOPE PATTERN DISCOVERY CONTEXT",
        f"Data Completeness Score: {analysis.data_completeness.overall_score_pct}%",
        f"- Cycles Logged: {analysis.data_completeness.cycles_logged_count}",
        f"- Symptom Log Dates: {analysis.data_completeness.symptoms_logged_days}",
        f"- Lifestyle Log Dates: {analysis.data_completeness.lifestyle_logged_days}",
        f"- Lab Biomarkers: {analysis.data_completeness.lab_biomarkers_count}",
        "",
        "## 1. Menstrual Cycle Pattern Analysis",
        f"- Rhythm: {analysis.cycle_patterns.rhythm_classification}",
        f"- Mean Length: {analysis.cycle_patterns.mean_length_days} days (StDev: {analysis.cycle_patterns.stdev_days})" if analysis.cycle_patterns.mean_length_days else "- No cycles logged",
        f"- Estimated Current Phase: {analysis.cycle_patterns.estimated_current_phase}",
        f"- Ovulation Status: {analysis.cycle_patterns.ovulation_confirmation_status}",
        f"- Clinical Interpretation: {analysis.cycle_patterns.clinical_interpretation}",
        "",
        "## 2. Top Symptom Clusters & Trends",
    ]

    for cluster in analysis.symptom_trends.top_clusters[:3]:
        co = ", ".join(cluster.co_occurring_symptoms) if cluster.co_occurring_symptoms else "None"
        prompt_lines.append(
            f"- {cluster.display_name}: {cluster.prevalence_pct}% prevalence (Avg Severity: {cluster.average_severity}/10, Trend: {cluster.trend_direction}, Co-occurring: {co})"
        )
    if not analysis.symptom_trends.top_clusters:
        prompt_lines.append("- No symptoms recorded in this window.")

    prompt_lines.extend(["", "## 3. Lifestyle-Symptom Statistical Correlations (N >= 7 Guard)"])
    for corr in analysis.lifestyle_correlations:
        if corr.has_sufficient_data and corr.correlation_coefficient is not None:
            prompt_lines.append(
                f"- {corr.factor_a} vs {corr.factor_b}: r = {corr.correlation_coefficient:+.2f} ({corr.strength} {corr.direction}) [N={corr.sample_size}]"
            )
        else:
            prompt_lines.append(f"- {corr.factor_a} vs {corr.factor_b}: Insufficient sample size (N={corr.sample_size} < 7)")

    prompt_lines.extend(["", "## 4. Laboratory Biomarker Trajectories"])
    for bio in analysis.biomarker_trajectories[:5]:
        prompt_lines.append(
            f"- {bio.biomarker_name}: Latest {bio.latest_value} {bio.latest_unit} ({bio.latest_status}) - Trajectory: {bio.trajectory_trend}"
        )
    if not analysis.biomarker_trajectories:
        prompt_lines.append("- No lab biomarkers recorded.")

    prompt_lines.extend(["", "## 5. Identified Clinical Care Gaps"])
    for gap in analysis.care_gaps:
        prompt_lines.append(f"- [{gap.priority}] {gap.title}: {gap.description}")

    prompt_lines.extend([
        "",
        "## TASK FOR CLINICAL AI ENGINE",
        "Synthesize these discovered patterns into an empathetic, evidence-grounded summary for the patient.",
        "RULES:",
        "1. Never claim confirmed ovulation without serum progesterone or ultrasound proof. Always refer to estimated phases as estimates.",
        "2. Clearly separate calculated metrics from observational statistical correlations.",
        "3. Emphasize that correlation does not establish causation.",
        "4. Provide 3-4 structured, actionable doctor discussion points.",
        "5. Do not invent lab values or clinical diagnoses.",
    ])

    full_prompt = "\n".join(prompt_lines)

    # 3. Attempt AI dispatch via Gemini/Groq
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    narrative_summary = ""
    key_observations: List[str] = []
    doctor_discussion_points: List[str] = []
    is_ai_generated = False

    try:
        response_text, provider_used, model_used = _dispatch_ai_request(prompt=full_prompt)
        narrative_summary = response_text
        is_ai_generated = True

        # Extract bullet observations from AI response
        for line in response_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("- ") or line_str.startswith("* "):
                key_observations.append(line_str.lstrip("-* ").strip())
        key_observations = key_observations[:5]

    except (AIEngineError, Exception) as exc:
        logger.warning("AI provider failed for PCOSCOPE insights (%s). Falling back to deterministic narrative.", exc)
        provider_used = "deterministic_fallback"
        model_used = "clinical_rule_engine"
        is_ai_generated = False

        # Deterministic Narrative Generation
        det_lines = [
            "### PCOSCOPE Health Pattern Summary (Deterministic Mode)",
            "External AI language services are currently offline. Below is your deterministic pattern summary generated directly from your authenticated clinical records:",
            "",
            f"**Cycle Rhythm**: {analysis.cycle_patterns.rhythm_classification}. Currently in {analysis.cycle_patterns.estimated_current_phase}.",
            f"**Data Completeness**: {analysis.data_completeness.overall_score_pct}% recorded. {analysis.data_completeness.recommendation}",
        ]

        if analysis.symptom_trends.top_clusters:
            top_s = analysis.symptom_trends.top_clusters[0]
            det_lines.append(
                f"**Primary Symptom**: {top_s.display_name} reported on {top_s.prevalence_pct}% of days with average severity {top_s.average_severity}/10 ({top_s.trend_direction} trend)."
            )

        sufficient_corrs = [c for c in analysis.lifestyle_correlations if c.has_sufficient_data and c.correlation_coefficient is not None]
        if sufficient_corrs:
            c = sufficient_corrs[0]
            det_lines.append(
                f"**Observed Association**: {c.factor_a} and {c.factor_b} show a {c.strength.lower()} {c.direction.lower()} correlation (r = {c.correlation_coefficient:+.2f}, N = {c.sample_size})."
            )
        else:
            det_lines.append(
                "**Lifestyle Correlations**: Insufficient paired daily check-ins (minimum 7 required) to determine statistical lifestyle-symptom relationships."
            )

        narrative_summary = "\n".join(det_lines)

    # 4. Generate structured doctor discussion points
    doctor_discussion_points = []
    if analysis.cycle_patterns.is_irregular:
        doctor_discussion_points.append(
            f"Discuss cycle irregularity: Recorded cycle intervals average {analysis.cycle_patterns.mean_length_days or 'variable'} days, meeting Monash 2023 irregular rhythm thresholds."
        )
    if any(g.category == "Laboratory" and "Glycemic" in g.title for g in analysis.care_gaps):
        doctor_discussion_points.append(
            "Request metabolic screening: Discuss whether fasting blood glucose, fasting insulin, or HbA1c is recommended at your upcoming visit."
        )
    if any(b.latest_status in ("Elevated", "Low", "Borderline / Impaired") for b in analysis.biomarker_trajectories):
        abnormals = [b.biomarker_name for b in analysis.biomarker_trajectories if b.latest_status in ("Elevated", "Low", "Borderline / Impaired")]
        doctor_discussion_points.append(
            f"Review out-of-range lab results: Evaluate recent findings for {', '.join(abnormals[:3])}."
        )
    if analysis.symptom_trends.top_clusters:
        top_sym = analysis.symptom_trends.top_clusters[0]
        doctor_discussion_points.append(
            f"Address persistent symptoms: Explore evidence-based strategies for managing recurrent {top_sym.display_name.lower()}."
        )
    if not doctor_discussion_points:
        doctor_discussion_points.append(
            "Review baseline PCOS health profile and discuss lifestyle management and preventive monitoring."
        )

    if not key_observations:
        key_observations = [
            f"Menstrual Rhythm: {analysis.cycle_patterns.rhythm_classification}",
            f"Record Completeness: {analysis.data_completeness.overall_score_pct}%",
            f"Care Gaps Identified: {len(analysis.care_gaps)} clinical items recommended",
        ]

    return PcoscopeInsightsResponse(
        analysis=analysis,
        narrative_summary=narrative_summary,
        key_observations=key_observations,
        doctor_discussion_points=doctor_discussion_points,
        provider_used=provider_used,
        model_used=model_used,
        is_ai_generated=is_ai_generated,
        disclaimer=STANDARD_DISCLAIMER,
    )
