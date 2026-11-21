"""Deterministic Clinical Calculators for PCOS360.

Pure mathematical, statistical, and rule-based clinical computations:
- Menstrual cycle rhythm and variance calculations (Monash 2023 guideline thresholds).
- Pearson correlation analysis with strict minimum sample-size guards.
- Configurable laboratory biomarker reference range evaluation.
- Rotterdam educational criteria assessment (decision-support, not automated diagnosis).
- Red-flag urgent symptom screening.

NOTE: All calculations use authentic user data and explicitly report when sample sizes
are insufficient. They do not invent data or predict outcomes without evidence.
"""

from dataclasses import dataclass, field
import math
import re
import statistics
from typing import Any, Dict, List, Optional, Tuple, Union

from app.core.medical_knowledge import (
    DEFAULT_BIOMARKER_RANGES,
    EDUCATIONAL_PHENOTYPES,
    MEDICAL_SOURCES,
    URGENT_RED_FLAGS,
    BiomarkerReferenceRange,
    RotterdamPillar,
)


@dataclass
class CycleAnalysisResult:
    sample_size: int
    has_sufficient_data: bool
    mean_length: Optional[float] = None
    median_length: Optional[float] = None
    stdev_length: Optional[float] = None
    min_length: Optional[int] = None
    max_length: Optional[int] = None
    rhythm_classification: str = "Insufficient Data"
    is_irregular: bool = False
    has_amenorrhea_flag: bool = False
    clinical_interpretation: str = ""
    guideline_reference: str = "Monash 2023 International PCOS Guideline"
    missing_data_note: Optional[str] = None


@dataclass
class CorrelationPairResult:
    factor_a: str
    factor_b: str
    sample_size: int
    has_sufficient_data: bool
    correlation_coefficient: Optional[float] = None
    direction: Optional[str] = None
    strength: Optional[str] = None
    interpretation: str = ""
    caveat: str = "Statistical correlation does not establish medical causation. Observational pattern only."


@dataclass
class BiomarkerEvaluationResult:
    biomarker_name: str
    canonical_name: str
    numeric_value: float
    reported_unit: Optional[str]
    standard_unit: str
    status: str  # Normal, Borderline / Impaired, Elevated, Low, Indeterminate
    reference_interval_applied: str
    is_custom_lab_range: bool
    clinical_significance: str
    cycle_phase_dependent: bool
    source_citation: str
    educational_note: str


@dataclass
class RotterdamAssessmentResult:
    criteria_evaluated: Dict[str, bool]
    criteria_present_count: int
    criteria_missing_documentation: List[str]
    educational_phenotype_alignment: str
    clinical_support_summary: str
    educational_disclaimer: str = (
        "Educational decision-support only. This is not an automated medical diagnosis. "
        "A formal PCOS diagnosis requires a clinical evaluation by a licensed physician to "
        "rule out confounding etiologies (e.g., thyroid dysfunction, hyperprolactinemia, "
        "congenital adrenal hyperplasia)."
    )


# ==============================================================================
# 1. Menstrual Cycle Statistics Calculator
# ==============================================================================

def calculate_cycle_statistics(cycles: List[Any]) -> CycleAnalysisResult:
    """Deterministically analyze menstrual cycle rhythms and regularity.

    Evaluated against Monash 2023 international consensus criteria:
    - Normal adult cycle interval: 21 to 35 days.
    - Oligomenorrhea / Delayed cycle: > 35 days.
    - Polymonorrhea / Short cycle: < 21 days.
    - Cycle variability / irregular rhythm: variance > 7-10 days between cycles.
    - Secondary amenorrhea flag: any interval >= 90 days.
    """
    lengths: List[int] = []

    for c in cycles:
        length_val = None
        if isinstance(c, dict):
            length_val = c.get("cycle_length") or c.get("length")
        elif hasattr(c, "cycle_length"):
            length_val = getattr(c, "cycle_length")
        elif isinstance(c, (int, float)):
            length_val = c

        if length_val is not None:
            try:
                val = int(length_val)
                if 10 <= val <= 365:  # filter impossible biological outliers
                    lengths.append(val)
            except (ValueError, TypeError):
                continue

    n = len(lengths)
    if n < 2:
        return CycleAnalysisResult(
            sample_size=n,
            has_sufficient_data=False,
            rhythm_classification="Insufficient Cycle History",
            clinical_interpretation=(
                f"Only {n} completed cycle recorded. At least 2 completed cycles are required "
                "to evaluate rhythm, length variability, and regularity."
            ),
            missing_data_note="Log at least 2 completed menstrual cycles to enable rhythm calculations.",
        )

    mean_val = round(statistics.mean(lengths), 1)
    median_val = round(statistics.median(lengths), 1)
    stdev_val = round(statistics.stdev(lengths), 1) if n >= 2 else 0.0
    min_val = min(lengths)
    max_val = max(lengths)
    has_amenorrhea = max_val >= 90

    # Monash 2023 regularity categorization
    is_irregular = False
    classification = "Regular Menstrual Rhythm"

    if has_amenorrhea:
        classification = "Amenorrhea Warning (>= 90 Days)"
        is_irregular = True
    elif mean_val > 35:
        classification = "Oligomenorrhea (Delayed Cycles > 35 Days)"
        is_irregular = True
    elif mean_val < 21:
        classification = "Polymenorrhea (Short Cycles < 21 Days)"
        is_irregular = True
    elif stdev_val > 7.0 or (max_val - min_val) > 10:
        classification = "Irregular Rhythm (High Cycle-to-Cycle Variance)"
        is_irregular = True

    interp = (
        f"Based on {n} documented cycles: average cycle length is {mean_val} days "
        f"(range: {min_val}–{max_val} days, standard deviation: {stdev_val} days). "
    )
    if is_irregular:
        interp += (
            f"Classified as '{classification}' per Monash 2023 clinical guidelines. "
            "Cycle irregularity is a key pillar of ovulatory dysfunction in PCOS."
        )
    else:
        interp += (
            "Cycle intervals fall within the standard 21–35 day clinical window with "
            "consistent rhythm (<7 days variation)."
        )

    return CycleAnalysisResult(
        sample_size=n,
        has_sufficient_data=True,
        mean_length=mean_val,
        median_length=median_val,
        stdev_length=stdev_val,
        min_length=min_val,
        max_length=max_val,
        rhythm_classification=classification,
        is_irregular=is_irregular,
        has_amenorrhea_flag=has_amenorrhea,
        clinical_interpretation=interp,
    )


# ==============================================================================
# 2. Pearson Correlation Calculator with Strict Sample Size Guards
# ==============================================================================

def _extract_date_str(item: Any) -> Optional[str]:
    d = None
    if isinstance(item, dict):
        d = (
            item.get("date")
            or item.get("log_date")
            or item.get("logged_date")
            or item.get("period_start_date")
            or item.get("report_date")
            or item.get("recorded_at")
            or item.get("created_at")
        )
    else:
        for attr in ["log_date", "date", "logged_date", "period_start_date", "report_date", "recorded_at", "created_at"]:
            if hasattr(item, attr) and getattr(item, attr) is not None:
                d = getattr(item, attr)
                break

    if d is not None:
        if hasattr(d, "strftime"):
            return d.strftime("%Y-%m-%d")
        return str(d)[:10]
    return None


def calculate_pearson_correlation(x_vals: List[float], y_vals: List[float]) -> Optional[float]:
    """Calculate Pearson correlation coefficient r between two paired numerical vectors.

    Returns None if vectors are shorter than 2 items or have zero variance.
    """
    if not x_vals or not y_vals or len(x_vals) != len(y_vals) or len(x_vals) < 2:
        return None

    try:
        var_x = statistics.variance(x_vals)
        var_y = statistics.variance(y_vals)
    except statistics.StatisticsError:
        return None

    if var_x == 0 or var_y == 0:
        return None

    mean_x = statistics.mean(x_vals)
    mean_y = statistics.mean(y_vals)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
    denominator = math.sqrt(sum((x - mean_x) ** 2 for x in x_vals) * sum((y - mean_y) ** 2 for y in y_vals))

    if denominator == 0:
        return 0.0
    return numerator / denominator


def calculate_symptom_correlations(
    daily_symptoms: List[Any],
    lifestyle_logs: List[Any],
    min_sample_size: int = 7,
) -> List[CorrelationPairResult]:
    """Calculate Pearson correlation coefficients between symptoms and lifestyle factors.

    STRICT SAFETY RULE:
    If fewer than `min_sample_size` (default: 7) paired daily logs exist,
    the calculator refuses to assert a correlation and explicitly reports insufficient data.
    """
    results: List[CorrelationPairResult] = []

    # Index by date
    symptom_by_date: Dict[str, Dict[str, float]] = {}
    for s in daily_symptoms:
        dt = _extract_date_str(s)
        if not dt:
            continue
        vals: Dict[str, float] = {}
        if isinstance(s, dict):
            fatigue_val = s.get("fatigue") if s.get("fatigue") is not None else s.get("fatigue_level")
            if fatigue_val is not None:
                vals["fatigue"] = float(fatigue_val)
            if "bloating" in s and s["bloating"] is not None:
                vals["bloating"] = float(s["bloating"])
            if "pelvic_pain" in s and s["pelvic_pain"] is not None:
                vals["pelvic_pain"] = float(s["pelvic_pain"])
            if "stress" in s and s["stress"] is not None:
                vals["stress"] = float(s["stress"])
            if "acne" in s and s["acne"] is not None:
                vals["acne"] = float(s["acne"])
            if "mood" in s and s["mood"] is not None:
                try:
                    vals["mood"] = float(s["mood"])
                except (ValueError, TypeError):
                    pass
        else:
            fatigue_val = getattr(s, "fatigue", None)
            if fatigue_val is None:
                fatigue_val = getattr(s, "fatigue_level", None)
            if fatigue_val is not None:
                try:
                    vals["fatigue"] = float(fatigue_val)
                except (ValueError, TypeError):
                    pass
            for attr in ["bloating", "pelvic_pain", "stress", "acne", "mood"]:
                if hasattr(s, attr) and getattr(s, attr) is not None:
                    try:
                        vals[attr] = float(getattr(s, attr))
                    except (ValueError, TypeError):
                        pass
        if vals:
            symptom_by_date[dt] = vals

    lifestyle_by_date: Dict[str, Dict[str, float]] = {}
    for l in lifestyle_logs:
        dt = _extract_date_str(l)
        if not dt:
            continue
        vals: Dict[str, float] = {}
        if isinstance(l, dict):
            if "sleep_hours" in l and l["sleep_hours"] is not None:
                vals["sleep_hours"] = float(l["sleep_hours"])
            if "stress_level" in l and l["stress_level"] is not None:
                vals["stress_level"] = float(l["stress_level"])
            w_val = l.get("water_intake")
            if w_val is not None:
                vals["water_glasses"] = float(w_val)
                vals["water_liters"] = float(w_val)
            if "water_glasses" in l and l["water_glasses"] is not None:
                vals["water_glasses"] = float(l["water_glasses"])
            if "water_liters" in l and l["water_liters"] is not None:
                vals["water_liters"] = float(l["water_liters"])
            if "exercise_minutes" in l and l["exercise_minutes"] is not None:
                vals["exercise_minutes"] = float(l["exercise_minutes"])
        else:
            w_val = getattr(l, "water_intake", None)
            if w_val is not None:
                try:
                    vals["water_glasses"] = float(w_val)
                    vals["water_liters"] = float(w_val)
                except (ValueError, TypeError):
                    pass
            for attr in ["sleep_hours", "stress_level", "water_glasses", "water_liters", "exercise_minutes"]:
                if hasattr(l, attr) and getattr(l, attr) is not None:
                    try:
                        vals[attr] = float(getattr(l, attr))
                    except (ValueError, TypeError):
                        pass
        if vals:
            lifestyle_by_date[dt] = vals

    # Pairings to examine
    pairs_to_test = [
        ("Sleep Duration (Hours)", "Fatigue Severity", "sleep_hours", "fatigue", "lifestyle", "symptom"),
        ("Perceived Stress Level", "Fatigue Severity", "stress_level", "fatigue", "lifestyle", "symptom"),
        ("Water Intake (Glasses)", "Bloating Severity", "water_glasses", "bloating", "lifestyle", "symptom"),
        ("Sleep Duration (Hours)", "Mood Disruption", "sleep_hours", "mood", "lifestyle", "symptom"),
    ]

    for label_a, label_b, key_a, key_b, src_a, src_b in pairs_to_test:
        x_vals: List[float] = []
        y_vals: List[float] = []

        all_dates = set(symptom_by_date.keys()).intersection(lifestyle_by_date.keys())
        for d in sorted(all_dates):
            val_a = lifestyle_by_date[d].get(key_a) if src_a == "lifestyle" else symptom_by_date[d].get(key_a)
            val_b = symptom_by_date[d].get(key_b) if src_b == "symptom" else lifestyle_by_date[d].get(key_b)
            if val_a is not None and val_b is not None:
                x_vals.append(val_a)
                y_vals.append(val_b)

        n = len(x_vals)
        if n < min_sample_size:
            results.append(
                CorrelationPairResult(
                    factor_a=label_a,
                    factor_b=label_b,
                    sample_size=n,
                    has_sufficient_data=False,
                    interpretation=(
                        f"Insufficient paired observations ({n} of {min_sample_size} required). "
                        "Keep logging daily symptoms and sleep to discover authentic mathematical patterns."
                    ),
                )
            )
            continue

        # Check for zero variance
        var_x = statistics.variance(x_vals) if n > 1 else 0
        var_y = statistics.variance(y_vals) if n > 1 else 0

        if var_x == 0 or var_y == 0:
            results.append(
                CorrelationPairResult(
                    factor_a=label_a,
                    factor_b=label_b,
                    sample_size=n,
                    has_sufficient_data=True,
                    correlation_coefficient=0.0,
                    direction="Neutral / Constant",
                    strength="None",
                    interpretation=f"No variance detected in logged values over {n} days.",
                )
            )
            continue

        # Compute Pearson r
        mean_x = statistics.mean(x_vals)
        mean_y = statistics.mean(y_vals)
        numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(x_vals, y_vals))
        denominator = math.sqrt(sum((x - mean_x) ** 2 for x in x_vals) * sum((y - mean_y) ** 2 for y in y_vals))

        if denominator == 0:
            r = 0.0
        else:
            r = round(numerator / denominator, 2)

        # Categorize
        abs_r = abs(r)
        if abs_r >= 0.7:
            strength_desc = "Strong"
        elif abs_r >= 0.4:
            strength_desc = "Moderate"
        elif abs_r >= 0.2:
            strength_desc = "Weak"
        else:
            strength_desc = "Negligible"

        direction_desc = "Positive" if r > 0.15 else ("Inverse / Negative" if r < -0.15 else "Neutral")

        interp_text = (
            f"Pearson correlation r = {r:+.2f} ({strength_desc} {direction_desc}) based on {n} matched daily logs. "
        )
        if r < -0.4:
            interp_text += f"Higher {label_a.lower()} shows an inverse relationship with reported {label_b.lower()}."
        elif r > 0.4:
            interp_text += f"Increases in {label_a.lower()} co-occur with higher reported {label_b.lower()}."
        else:
            interp_text += f"No strong linear co-occurrence observed in current logs."

        results.append(
            CorrelationPairResult(
                factor_a=label_a,
                factor_b=label_b,
                sample_size=n,
                has_sufficient_data=True,
                correlation_coefficient=r,
                direction=direction_desc,
                strength=strength_desc,
                interpretation=interp_text,
            )
        )

    return results


# ==============================================================================
# 3. Configurable Biomarker Evaluator
# ==============================================================================

def _find_biomarker_config(name: str) -> Optional[BiomarkerReferenceRange]:
    cleaned = name.strip().lower()
    for _, config in DEFAULT_BIOMARKER_RANGES.items():
        if cleaned == config.biomarker_name.lower():
            return config
        for alias in config.canonical_aliases:
            if alias in cleaned or cleaned in alias:
                return config
    return None


def _parse_lab_range(range_str: str) -> Tuple[Optional[float], Optional[float]]:
    """Attempt to parse custom lab reference interval strings like '70 - 99', '< 5.7', '> 50'."""
    s = range_str.strip().replace(",", ".")
    # Range 'A - B'
    m_between = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)", s)
    if m_between:
        return float(m_between.group(1)), float(m_between.group(2))

    # Upper ceiling '< X'
    m_less = re.search(r"(?:<|<=|less than|up to)\s*(\d+(?:\.\d+)?)", s, re.IGNORECASE)
    if m_less:
        return None, float(m_less.group(1))

    # Lower floor '> X'
    m_more = re.search(r"(?:>|>=|greater than|at least)\s*(\d+(?:\.\d+)?)", s, re.IGNORECASE)
    if m_more:
        return float(m_more.group(1)), None

    return None, None


def evaluate_biomarker(
    test_name: str,
    value: Union[float, int, str],
    unit: Optional[str] = None,
    lab_normal_range: Optional[str] = None,
) -> BiomarkerEvaluationResult:
    """Evaluate a laboratory biomarker against configurable reference ranges.

    Prioritizes the reference range reported by the performing laboratory;
    falls back to standard clinical chemistry guidelines when unspecified.
    """
    try:
        numeric_val = float(str(value).strip().replace(",", ".").replace("%", ""))
    except (ValueError, TypeError):
        return BiomarkerEvaluationResult(
            biomarker_name=test_name,
            canonical_name=test_name,
            numeric_value=0.0,
            reported_unit=unit,
            standard_unit=unit or "unit",
            status="Indeterminate",
            reference_interval_applied="Invalid numeric value",
            is_custom_lab_range=False,
            clinical_significance="Could not parse numeric laboratory result.",
            cycle_phase_dependent=False,
            source_citation="N/A",
            educational_note="Please verify the test value with your original lab report.",
        )

    config = _find_biomarker_config(test_name)
    canonical = config.biomarker_name if config else test_name
    std_unit = config.standard_unit if config else (unit or "")
    source_cite = config.primary_source if config else "Diagnostic Laboratory Report"
    phase_dep = config.cycle_phase_dependent if config else False
    clin_sig = config.clinical_significance if config else "Biomarker assessment."

    # Determine reference range to use
    custom_low, custom_high = (None, None)
    if lab_normal_range and lab_normal_range.strip():
        custom_low, custom_high = _parse_lab_range(lab_normal_range)

    is_custom = custom_low is not None or custom_high is not None

    if is_custom:
        ref_text = lab_normal_range.strip()
        low_bound = custom_low
        high_bound = custom_high
    elif config:
        low_bound = config.normal_low
        high_bound = config.normal_high
        if low_bound is not None and high_bound is not None:
            ref_text = f"{low_bound} – {high_bound} {std_unit}"
        elif high_bound is not None:
            ref_text = f"< {high_bound} {std_unit}"
        elif low_bound is not None:
            ref_text = f"> {low_bound} {std_unit}"
        else:
            ref_text = f"Assay-dependent ({std_unit})"
    else:
        ref_text = lab_normal_range or "Not specified by reporting lab"
        low_bound = None
        high_bound = None

    # Status classification
    status = "Normal"
    if high_bound is not None and numeric_val > high_bound:
        if config and config.borderline_high is not None and numeric_val <= config.borderline_high:
            status = "Borderline / Impaired"
        else:
            status = "Elevated"
    elif low_bound is not None and numeric_val < low_bound:
        if config and config.borderline_low is not None and numeric_val >= config.borderline_low:
            status = "Borderline / Low"
        else:
            status = "Low"

    ed_note = (
        f"{canonical}: {numeric_val} {unit or std_unit} (Reference: {ref_text}). Status: {status}. "
    )
    if status != "Normal":
        ed_note += (
            "Educational note: Values outside reference limits should be discussed with "
            "your treating clinician alongside clinical history and symptoms."
        )
    else:
        ed_note += "Within reference limits for this parameter."

    return BiomarkerEvaluationResult(
        biomarker_name=test_name,
        canonical_name=canonical,
        numeric_value=numeric_val,
        reported_unit=unit,
        standard_unit=std_unit,
        status=status,
        reference_interval_applied=ref_text,
        is_custom_lab_range=is_custom,
        clinical_significance=clin_sig,
        cycle_phase_dependent=phase_dep,
        source_citation=source_cite,
        educational_note=ed_note,
    )


# ==============================================================================
# 4. Rotterdam Consensus Educational Decision-Support Assessment
# ==============================================================================

def assess_rotterdam_criteria_educational(
    profile: Optional[Any],
    cycles: List[Any],
    symptoms: List[Any],
    lab_reports: List[Any],
    clinical_records: List[Any],
) -> RotterdamAssessmentResult:
    """Evaluate clinical pillars under Rotterdam criteria using authentic records.

    EDUCATIONAL DECISION-SUPPORT ONLY:
    - Never automates or issues a formal diagnosis.
    - Explicitly lists missing tests (e.g. pelvic ultrasound, thyroid panel).
    """
    criteria_evaluated: Dict[str, bool] = {
        RotterdamPillar.OVULATORY_DYSFUNCTION.value: False,
        RotterdamPillar.HYPERANDROGENISM.value: False,
        RotterdamPillar.POLYCYSTIC_MORPHOLOGY.value: False,
    }
    missing_docs: List[str] = []

    # Pillar 1: Ovulatory dysfunction
    cycle_stats = calculate_cycle_statistics(cycles)
    if cycle_stats.has_sufficient_data:
        if cycle_stats.is_irregular:
            criteria_evaluated[RotterdamPillar.OVULATORY_DYSFUNCTION.value] = True
    else:
        missing_docs.append("Menstrual cycle tracking history (< 2 completed cycles on file)")

    # Pillar 2: Hyperandrogenism (Biochemical or Clinical)
    has_hyperandrogenism = False

    # Check biochemical labs
    has_androgen_lab = False
    for r in lab_reports:
        tests = []
        if isinstance(r, dict):
            if "tests" in r:
                tests = r.get("tests") or []
            elif "test_name" in r:
                tests = [{"name": r.get("test_name"), "value": r.get("test_value"), "unit": r.get("unit"), "reference_range": r.get("reference_range")}]
        else:
            if hasattr(r, "tests") and getattr(r, "tests"):
                tests = getattr(r, "tests")
            elif hasattr(r, "test_name") and hasattr(r, "test_value"):
                tests = [{"name": getattr(r, "test_name"), "value": getattr(r, "test_value"), "unit": getattr(r, "unit", None), "reference_range": getattr(r, "reference_range", None)}]

        for t in tests:
            name = (t.get("name") if isinstance(t, dict) else getattr(t, "name", "")) or ""
            val = t.get("value") if isinstance(t, dict) else getattr(t, "value", None)
            ref_rng = t.get("reference_range") if isinstance(t, dict) else getattr(t, "reference_range", None)
            unit_val = t.get("unit") if isinstance(t, dict) else getattr(t, "unit", None)
            if any(k in name.lower() for k in ["testosterone", "dhea", "free androgen"]):
                has_androgen_lab = True
                ev = evaluate_biomarker(name, val, unit=unit_val, lab_normal_range=ref_rng)
                if ev.status in ["Elevated", "Borderline / Impaired"]:
                    has_hyperandrogenism = True

    # Check clinical records direct androgen biomarkers & signs
    has_clinical_androgen = False
    for rec in clinical_records:
        t_val = rec.get("testosterone") if isinstance(rec, dict) else getattr(rec, "testosterone", None)
        ft_val = rec.get("free_testosterone") if isinstance(rec, dict) else getattr(rec, "free_testosterone", None)
        dheas_val = rec.get("dheas") if isinstance(rec, dict) else getattr(rec, "dheas", None)

        if t_val is not None:
            has_androgen_lab = True
            ev = evaluate_biomarker("Total Testosterone", t_val)
            if ev.status in ["Elevated", "Borderline / Impaired"]:
                has_hyperandrogenism = True
        if ft_val is not None:
            has_androgen_lab = True
            ev = evaluate_biomarker("Free Testosterone", ft_val)
            if ev.status in ["Elevated", "Borderline / Impaired"]:
                has_hyperandrogenism = True
        if dheas_val is not None:
            has_androgen_lab = True
            ev = evaluate_biomarker("DHEA-S", dheas_val)
            if ev.status in ["Elevated", "Borderline / Impaired"]:
                has_hyperandrogenism = True

        hirsutism_score = None
        if isinstance(rec, dict):
            hirsutism_score = rec.get("ferriman_gallwey_score")
        elif hasattr(rec, "ferriman_gallwey_score"):
            hirsutism_score = getattr(rec, "ferriman_gallwey_score")

        if hirsutism_score is not None and hirsutism_score >= 4:  # ethnic-specific cutoffs start at 4-6
            has_clinical_androgen = True

    # Check daily symptoms for clinical hyperandrogenism signs
    for sym in (symptoms or []):
        unwanted_hair = sym.get("unwanted_hair_growth") if isinstance(sym, dict) else getattr(sym, "unwanted_hair_growth", None)
        acne = sym.get("acne_severity") if isinstance(sym, dict) else getattr(sym, "acne_severity", None)
        if unwanted_hair and str(unwanted_hair).lower() in ["moderate", "severe"]:
            has_clinical_androgen = True
        if acne and str(acne).lower() in ["moderate", "severe"]:
            has_clinical_androgen = True

    if has_hyperandrogenism or has_clinical_androgen:
        criteria_evaluated[RotterdamPillar.HYPERANDROGENISM.value] = True
    elif not has_androgen_lab:
        missing_docs.append("Serum androgen laboratory panel (Total/Free Testosterone or DHEA-S)")

    # Pillar 3: Polycystic Ovarian Morphology (PCOM)
    has_ultrasound = False
    has_pcom = False
    for rec in clinical_records:
        notes = ""
        follicle_count = None
        if isinstance(rec, dict):
            notes = rec.get("ultrasound_findings") or rec.get("ultrasound_notes") or ""
            follicle_count = rec.get("antral_follicle_count")
        else:
            notes = getattr(rec, "ultrasound_findings", "") or getattr(rec, "ultrasound_notes", "") or ""
            follicle_count = getattr(rec, "antral_follicle_count", None)

        if notes or follicle_count is not None:
            has_ultrasound = True
            if follicle_count is not None and follicle_count >= 20:  # Monash 2023 >= 20 follicles/ovary
                has_pcom = True
            elif any(w in notes.lower() for w in ["polycystic", "pcom", "string of pearls", "increased ovarian volume", "follicles >= 20"]):
                has_pcom = True

    if has_pcom:
        criteria_evaluated[RotterdamPillar.POLYCYSTIC_MORPHOLOGY.value] = True
    elif not has_ultrasound:
        missing_docs.append("Pelvic ultrasound imaging notes (Antral follicle count & ovarian volume)")

    # Count positive pillars
    present_count = sum(1 for v in criteria_evaluated.values() if v is True)

    # Educational phenotype mapping
    c1 = criteria_evaluated[RotterdamPillar.OVULATORY_DYSFUNCTION.value]
    c2 = criteria_evaluated[RotterdamPillar.HYPERANDROGENISM.value]
    c3 = criteria_evaluated[RotterdamPillar.POLYCYSTIC_MORPHOLOGY.value]

    if c1 and c2 and c3:
        alignment = "Phenotype A (Classic / Complete: Criteria 1 + 2 + 3 documented)"
    elif c1 and c2 and not c3:
        if not has_ultrasound:
            alignment = "Potential Phenotype B (Non-PCOM) or Phenotype A (Pending pelvic ultrasound review)"
        else:
            alignment = "Phenotype B (Non-PCOM: Hyperandrogenism + Ovulatory dysfunction with normal ultrasound)"
    elif c2 and c3 and not c1:
        alignment = "Phenotype C (Ovulatory: Hyperandrogenism + Polycystic morphology with regular cycles)"
    elif c1 and c3 and not c2:
        alignment = "Phenotype D (Non-Hyperandrogenic: Ovulatory dysfunction + Polycystic morphology)"
    else:
        alignment = f"Incomplete Clinical Profile ({present_count} of 2 required criteria documented)"

    summary = (
        f"Documented features evaluated under Rotterdam criteria: "
        f"{present_count} of 3 pillars present in user records. "
    )
    if missing_docs:
        summary += f"Missing documentary evidence: {'; '.join(missing_docs)}. "
    summary += (
        "Educational framework: Monash 2023 consensus requires 2 of 3 features in adults after "
        "excluding related conditions. Discuss findings with your gynecologist or endocrinologist."
    )

    return RotterdamAssessmentResult(
        criteria_evaluated=criteria_evaluated,
        criteria_present_count=present_count,
        criteria_missing_documentation=missing_docs,
        educational_phenotype_alignment=alignment,
        clinical_support_summary=summary,
    )


# ==============================================================================
# 5. Red-Flag Urgent Symptom Screener
# ==============================================================================

def screen_urgent_symptoms(
    symptoms: List[str],
    notes: Optional[str] = None,
) -> Dict[str, Any]:
    """Scan symptoms and free-text notes for urgent clinical red flags.

    Detects potential emergencies (ovarian cyst rupture, ovarian torsion, severe menorrhagia)
    and provides immediate triage escalation guidance.
    """
    combined_text = " ".join(symptoms or [])
    if notes:
        combined_text += " " + notes

    flags_found: List[Dict[str, str]] = []

    for flag in URGENT_RED_FLAGS:
        if re.search(flag["pattern"], combined_text, re.IGNORECASE):
            flags_found.append({
                "id": flag["id"],
                "concern": flag["concern"],
                "urgency": flag["urgency"],
                "action": flag["action"],
            })

    if flags_found:
        return {
            "has_urgent_symptoms": True,
            "urgency_level": "URGENT_EVALUATION_RECOMMENDED",
            "flags_detected": flags_found,
            "escalation_message": (
                "⚠️ IMPORTANT SAFETY ALERT: One or more reported symptoms warrant urgent medical "
                "evaluation to rule out acute complications (e.g., ovarian torsion, acute cyst rupture, "
                "or heavy hemorrhage). Please contact a healthcare professional or visit urgent care promptly."
            ),
        }

    return {
        "has_urgent_symptoms": False,
        "urgency_level": "ROUTINE",
        "flags_detected": [],
        "escalation_message": "No urgent clinical red flags detected in current entries.",
    }

