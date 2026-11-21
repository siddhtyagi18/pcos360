"""Comprehensive unit tests for PCOS360 Phase 1 Deterministic Clinical Calculators & Knowledge Base."""

import unittest
from datetime import date, timedelta

from app.core.medical_knowledge import (
    DEFAULT_BIOMARKER_RANGES,
    MEDICAL_SOURCES,
    URGENT_RED_FLAGS,
    RotterdamPillar,
)
from app.services.clinical_calculator import (
    calculate_cycle_statistics,
    calculate_symptom_correlations,
    evaluate_biomarker,
    assess_rotterdam_criteria_educational,
    screen_urgent_symptoms,
)


class TestClinicalCalculators(unittest.TestCase):
    """Test suite verifying mathematical accuracy, sample-size guards, and guideline alignment."""

    # --------------------------------------------------------------------------
    # 1. Menstrual Cycle Statistics Tests
    # --------------------------------------------------------------------------

    def test_cycle_statistics_empty_and_insufficient_data(self):
        # 0 cycles
        res_zero = calculate_cycle_statistics([])
        self.assertFalse(res_zero.has_sufficient_data)
        self.assertEqual(res_zero.sample_size, 0)
        self.assertIn("Insufficient", res_zero.rhythm_classification)
        self.assertIsNotNone(res_zero.missing_data_note)

        # 1 cycle (insufficient to compute rhythm or variance)
        res_one = calculate_cycle_statistics([{"cycle_length": 28}])
        self.assertFalse(res_one.has_sufficient_data)
        self.assertEqual(res_one.sample_size, 1)

    def test_cycle_statistics_regular_rhythm(self):
        cycles = [
            {"cycle_length": 28},
            {"cycle_length": 29},
            {"cycle_length": 27},
            {"cycle_length": 28},
        ]
        res = calculate_cycle_statistics(cycles)
        self.assertTrue(res.has_sufficient_data)
        self.assertEqual(res.sample_size, 4)
        self.assertEqual(res.mean_length, 28.0)
        self.assertEqual(res.median_length, 28.0)
        self.assertFalse(res.is_irregular)
        self.assertEqual(res.rhythm_classification, "Regular Menstrual Rhythm")

    def test_cycle_statistics_oligomenorrhea(self):
        # Monash 2023: Mean interval > 35 days represents oligomenorrhea
        cycles = [
            {"cycle_length": 38},
            {"cycle_length": 42},
            {"cycle_length": 36},
            {"cycle_length": 40},
        ]
        res = calculate_cycle_statistics(cycles)
        self.assertTrue(res.has_sufficient_data)
        self.assertEqual(res.mean_length, 39.0)
        self.assertTrue(res.is_irregular)
        self.assertIn("Oligomenorrhea", res.rhythm_classification)

    def test_cycle_statistics_high_variance_irregularity(self):
        # Monash 2023: High cycle-to-cycle variance (>7 days standard deviation)
        cycles = [
            {"cycle_length": 23},
            {"cycle_length": 44},
            {"cycle_length": 25},
            {"cycle_length": 39},
        ]
        res = calculate_cycle_statistics(cycles)
        self.assertTrue(res.has_sufficient_data)
        self.assertTrue(res.is_irregular)
        self.assertGreater(res.stdev_length, 7.0)
        self.assertIn("Irregular", res.rhythm_classification)

    def test_cycle_statistics_amenorrhea_flag(self):
        # Secondary amenorrhea flag: any interval >= 90 days
        cycles = [
            {"cycle_length": 32},
            {"cycle_length": 95},
        ]
        res = calculate_cycle_statistics(cycles)
        self.assertTrue(res.has_sufficient_data)
        self.assertTrue(res.has_amenorrhea_flag)
        self.assertIn("Amenorrhea Warning", res.rhythm_classification)

    # --------------------------------------------------------------------------
    # 2. Pearson Correlation & Sample-Size Guard Tests
    # --------------------------------------------------------------------------

    def test_symptom_correlations_insufficient_sample_size_refuses_assertion(self):
        # Only 4 matched logs (fewer than the required 7)
        symptoms = [
            {"date": f"2026-01-0{i}", "fatigue": 7 - i, "bloating": 4} for i in range(1, 5)
        ]
        lifestyle = [
            {"date": f"2026-01-0{i}", "sleep_hours": 6.0 + i * 0.5, "stress_level": 5} for i in range(1, 5)
        ]

        results = calculate_symptom_correlations(symptoms, lifestyle, min_sample_size=7)
        self.assertGreater(len(results), 0)

        for r in results:
            self.assertFalse(r.has_sufficient_data)
            self.assertIsNone(r.correlation_coefficient)
            self.assertIn("Insufficient paired observations", r.interpretation)

    def test_symptom_correlations_valid_sample_computes_pearson_r(self):
        # 10 matched logs with an inverse correlation (more sleep = less fatigue)
        symptoms = []
        lifestyle = []
        base_date = date(2026, 1, 1)

        for i in range(10):
            d_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            # Sleep increases from 5h to 9.5h
            sleep_h = 5.0 + (i * 0.5)
            # Fatigue decreases from 9 to 1
            fatigue_score = 9.0 - (i * 0.8)

            lifestyle.append({"date": d_str, "sleep_hours": sleep_h, "stress_level": 5})
            symptoms.append({"date": d_str, "fatigue": fatigue_score, "bloating": 3})

        results = calculate_symptom_correlations(symptoms, lifestyle, min_sample_size=7)
        sleep_fatigue = next((r for r in results if r.factor_a == "Sleep Duration (Hours)" and r.factor_b == "Fatigue Severity"), None)

        self.assertIsNotNone(sleep_fatigue)
        self.assertTrue(sleep_fatigue.has_sufficient_data)
        self.assertEqual(sleep_fatigue.sample_size, 10)
        self.assertIsNotNone(sleep_fatigue.correlation_coefficient)
        self.assertLess(sleep_fatigue.correlation_coefficient, -0.8)
        self.assertEqual(sleep_fatigue.direction, "Inverse / Negative")
        self.assertEqual(sleep_fatigue.strength, "Strong")
        self.assertIn("does not establish medical causation", sleep_fatigue.caveat)

    def test_symptom_correlations_zero_variance_does_not_crash(self):
        # Constant fatigue and constant sleep
        symptoms = [{"date": f"2026-01-{i:02d}", "fatigue": 5.0} for i in range(1, 10)]
        lifestyle = [{"date": f"2026-01-{i:02d}", "sleep_hours": 7.0} for i in range(1, 10)]

        results = calculate_symptom_correlations(symptoms, lifestyle, min_sample_size=7)
        pair = results[0]
        self.assertTrue(pair.has_sufficient_data)
        self.assertEqual(pair.correlation_coefficient, 0.0)
        self.assertEqual(pair.strength, "None")

    # --------------------------------------------------------------------------
    # 3. Laboratory Biomarker Evaluation Tests
    # --------------------------------------------------------------------------

    def test_biomarker_evaluation_standard_reference_ranges(self):
        # Normal HbA1c (< 5.7%)
        eval_normal = evaluate_biomarker("HbA1c", 5.4, unit="%")
        self.assertEqual(eval_normal.status, "Normal")
        self.assertEqual(eval_normal.canonical_name, "HbA1c (Glycated Hemoglobin)")

        # Borderline HbA1c (5.7% - 6.4%)
        eval_border = evaluate_biomarker("HbA1c", 5.8, unit="%")
        self.assertEqual(eval_border.status, "Borderline / Impaired")

        # Elevated HbA1c (>= 6.5%)
        eval_elev = evaluate_biomarker("HbA1c", 6.8, unit="%")
        self.assertEqual(eval_elev.status, "Elevated")

        # Fasting Insulin (Normal < 10, Borderline 10-25, Elevated > 25)
        eval_ins_norm = evaluate_biomarker("Fasting Insulin", 7.5, unit="μIU/mL")
        self.assertEqual(eval_ins_norm.status, "Normal")

        eval_ins_border = evaluate_biomarker("Fasting Insulin", 14.2, unit="μIU/mL")
        self.assertEqual(eval_ins_border.status, "Borderline / Impaired")

        eval_ins_high = evaluate_biomarker("Fasting Insulin", 29.0, unit="μIU/mL")
        self.assertEqual(eval_ins_high.status, "Elevated")

        # Cycle phase dependency flag for LH / FSH ratio
        eval_lh = evaluate_biomarker("LH / FSH Ratio", 2.3)
        self.assertEqual(eval_lh.status, "Elevated")
        self.assertTrue(eval_lh.cycle_phase_dependent)

    def test_biomarker_evaluation_custom_lab_range_override(self):
        # Reporting lab specifies custom reference interval "70 - 105"
        # 102 mg/dL would be borderline under standard (99 ceiling), but NORMAL under this custom lab report
        eval_custom = evaluate_biomarker(
            "Fasting Blood Glucose",
            102.0,
            unit="mg/dL",
            lab_normal_range="70 - 105 mg/dL",
        )
        self.assertTrue(eval_custom.is_custom_lab_range)
        self.assertEqual(eval_custom.status, "Normal")
        self.assertEqual(eval_custom.reference_interval_applied, "70 - 105 mg/dL")

    def test_biomarker_evaluation_invalid_value_handles_gracefully(self):
        eval_invalid = evaluate_biomarker("HbA1c", "Not_A_Number")
        self.assertEqual(eval_invalid.status, "Indeterminate")
        self.assertIn("Invalid", eval_invalid.reference_interval_applied)

    # --------------------------------------------------------------------------
    # 4. Rotterdam Educational Criteria Assessment Tests
    # --------------------------------------------------------------------------

    def test_rotterdam_assessment_phenotype_a_complete(self):
        # 1. Oligo/anovulation (delayed cycles)
        cycles = [{"cycle_length": 39}, {"cycle_length": 42}, {"cycle_length": 37}]
        # 2. Hyperandrogenism (Elevated testosterone)
        labs = [{"tests": [{"name": "Total Testosterone", "value": 58, "unit": "ng/dL"}]}]
        # 3. PCOM (Ultrasound notes)
        clinical = [{"ultrasound_notes": "Polycystic ovarian morphology noted bilateral, AFC > 20"}]

        res = assess_rotterdam_criteria_educational(
            profile=None,
            cycles=cycles,
            symptoms=[],
            lab_reports=labs,
            clinical_records=clinical,
        )

        self.assertEqual(res.criteria_present_count, 3)
        self.assertIn("Phenotype A", res.educational_phenotype_alignment)
        self.assertEqual(len(res.criteria_missing_documentation), 0)
        self.assertIn("not an automated medical diagnosis", res.educational_disclaimer)

    def test_rotterdam_assessment_missing_ultrasound_identifies_missing_data(self):
        # Only cycles and labs, ultrasound missing
        cycles = [{"cycle_length": 40}, {"cycle_length": 45}]
        labs = [{"tests": [{"name": "Total Testosterone", "value": 60, "unit": "ng/dL"}]}]

        res = assess_rotterdam_criteria_educational(
            profile=None,
            cycles=cycles,
            symptoms=[],
            lab_reports=labs,
            clinical_records=[],
        )

        self.assertEqual(res.criteria_present_count, 2)
        # Should identify missing imaging notes
        self.assertTrue(any("ultrasound" in m.lower() for m in res.criteria_missing_documentation))
        self.assertIn("Pending pelvic ultrasound", res.educational_phenotype_alignment)

    def test_rotterdam_assessment_empty_profile_reports_all_missing(self):
        res = assess_rotterdam_criteria_educational(
            profile=None,
            cycles=[],
            symptoms=[],
            lab_reports=[],
            clinical_records=[],
        )
        self.assertEqual(res.criteria_present_count, 0)
        self.assertGreaterEqual(len(res.criteria_missing_documentation), 3)

    # --------------------------------------------------------------------------
    # 5. Urgent Red-Flag Symptom Screening Tests
    # --------------------------------------------------------------------------

    def test_screen_urgent_symptoms_routine(self):
        routine_symptoms = ["Mild bloating", "Occasional acne", "Mild luteal fatigue"]
        res = screen_urgent_symptoms(routine_symptoms, notes="Feeling a bit tired today.")
        self.assertFalse(res["has_urgent_symptoms"])
        self.assertEqual(res["urgency_level"], "ROUTINE")
        self.assertEqual(len(res["flags_detected"]), 0)

    def test_screen_urgent_symptoms_detects_acute_pain(self):
        urgent_symptoms = ["Severe acute pelvic pain on right side", "Nausea"]
        res = screen_urgent_symptoms(urgent_symptoms, notes="Pain is sudden, sharp, and unbearable.")
        self.assertTrue(res["has_urgent_symptoms"])
        self.assertEqual(res["urgency_level"], "URGENT_EVALUATION_RECOMMENDED")
        self.assertGreater(len(res["flags_detected"]), 0)
        self.assertEqual(res["flags_detected"][0]["id"], "acute_pelvic_pain")
        self.assertIn("SAFETY ALERT", res["escalation_message"])

    def test_screen_urgent_symptoms_detects_severe_hemorrhage(self):
        res = screen_urgent_symptoms(["Heavy bleeding"], notes="I have been bleeding through 2 pads per hour for the past 3 hours.")
        self.assertTrue(res["has_urgent_symptoms"])
        self.assertEqual(res["flags_detected"][0]["id"], "menorrhagia_hemorrhage")


if __name__ == "__main__":
    unittest.main()

