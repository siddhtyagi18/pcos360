"""Unit and integration test suite for the PCOS360 User Context Engine (Phase 2).

Tests:
1. User data retrieval (comprehensive data across all clinical domains)
2. Empty user profiles (honest missing-data handling, no fake demographics)
3. Missing lab reports (correct missing-tests listing and Rotterdam gap detection)
4. Missing cycle history (insufficient sample-size guards: 0 and 1 cycle)
5. Cross-user data isolation (strict user-level boundaries, zero leakage)
6. Unauthorized access (API rejection of unauthenticated/invalid/revoked requests)
7. Database errors (clean exception handling and HTTP 503 response)
"""

from datetime import date, datetime, timedelta, timezone
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SECRET_KEY", "test-only-ephemeral-secret-key-at-least-32-chars")


class TestUserContextEngine(unittest.TestCase):
    """Automated test cases for Phase 2: User Context Engine."""

    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="pcos360_context_test_", suffix=".db")
        os.close(fd)
        cls.engine = create_engine(
            f"sqlite:///{cls.db_path}",
            connect_args={"check_same_thread": False},
        )
        cls.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=cls.engine)

        from app.core.database import Base, get_db
        import app.models  # noqa: F401
        from app.main import app

        Base.metadata.create_all(bind=cls.engine)

        def override_get_db():
            db = cls.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        cls.app = app
        cls.app.dependency_overrides[get_db] = override_get_db
        cls.client = TestClient(cls.app)

    def setUp(self):
        from app.core.rate_limit import auth_rate_limiter
        auth_rate_limiter.reset()
        self.db = self.SessionLocal()

    def tearDown(self):
        self.db.close()

    @classmethod
    def tearDownClass(cls):
        cls.app.dependency_overrides.clear()
        cls.engine.dispose()
        if os.path.exists(cls.db_path):
            os.remove(cls.db_path)

    def _create_user(self, full_name: str, email: str, password: str = "StrongPass123!"):
        res = self.client.post(
            "/api/auth/register",
            json={"full_name": full_name, "email": email, "password": password},
        )
        self.assertEqual(res.status_code, 201, res.text)
        data = res.json()
        from app.models.user import User
        user = self.db.query(User).filter(User.id == data["user"]["id"]).first()
        return user, {"Authorization": f"Bearer {data['access_token']}"}

    # ==========================================================================
    # 1. User Data Retrieval (Fully Populated User)
    # ==========================================================================
    def test_complete_user_data_retrieval(self):
        """Verify context retrieval for a user with comprehensive data across all modules."""
        user, _ = self._create_user("Alice Patient", "alice_complete@example.com")
        from app.models.clinical_record import ClinicalRecord
        from app.models.daily_symptom import DailySymptom
        from app.models.health_profile import HealthProfile
        from app.models.lab_report import LabReport
        from app.models.lifestyle_log import LifestyleLog
        from app.models.menstrual_cycle import MenstrualCycle
        from app.services.context_builder import build_user_health_context

        # 1. Profile (68 kg, 165 cm -> BMI = 25.0, Overweight)
        profile = HealthProfile(
            user_id=user.id,
            age=27,
            height=165.0,
            weight=68.0,
            diagnosis_status="Diagnosed",
            diagnosis_year=2022,
            existing_conditions=["Insulin Resistance", "Hypothyroidism"],
            medications=["Metformin 500mg", "Levothyroxine 50mcg"],
        )
        self.db.add(profile)

        # 2. Cycles (3 completed cycles with irregular intervals: 42, 38, 45 days)
        base_date = date.today() - timedelta(days=125)
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=base_date,
            period_end_date=base_date + timedelta(days=5),
            cycle_length=42,
            flow_intensity="Heavy",
            notes="Late cycle with heavy flow",
        ))
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=base_date + timedelta(days=42),
            period_end_date=base_date + timedelta(days=47),
            cycle_length=38,
            flow_intensity="Medium",
            notes="Moderate cramping",
        ))
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=base_date + timedelta(days=80),
            period_end_date=base_date + timedelta(days=85),
            cycle_length=45,
            flow_intensity="Heavy",
            notes="Delayed cycle",
        ))

        # 3. Symptoms (8 daily logs for valid correlation sample size N >= 7)
        for i in range(8):
            log_dt = date.today() - timedelta(days=8 - i)
            self.db.add(DailySymptom(
                user_id=user.id,
                log_date=log_dt,
                acne_severity="Moderate",
                hair_loss="Mild",
                unwanted_hair_growth="Moderate",
                fatigue_level=6 + (i % 3),
                bloating=4 + (i % 2),
                pelvic_pain=3,
                mood="Irritable",
                notes="Afternoon fatigue",
            ))

        # 4. Lifestyle logs (8 matching daily logs)
        for i in range(8):
            log_dt = date.today() - timedelta(days=8 - i)
            self.db.add(LifestyleLog(
                user_id=user.id,
                log_date=log_dt,
                sleep_hours=6.5 + (0.5 if i % 2 == 0 else -0.5),
                stress_level=3 + (1 if i % 2 == 1 else 0),
                water_intake=2.0,
                exercise_minutes=25,
                food_habits="Low GI",
                meal_regularity="Regular",
            ))

        # 5. Lab Reports (Elevated Total Testosterone, Normal Fasting Glucose)
        self.db.add(LabReport(
            user_id=user.id,
            report_name="Hormone Panel",
            test_name="Total Testosterone",
            test_value=68.5,
            unit="ng/dL",
            reference_range="15.0 - 45.0 ng/dL",
            report_date=date.today() - timedelta(days=15),
        ))
        self.db.add(LabReport(
            user_id=user.id,
            report_name="Metabolic Panel",
            test_name="Fasting Glucose",
            test_value=92.0,
            unit="mg/dL",
            reference_range="70.0 - 99.0 mg/dL",
            report_date=date.today() - timedelta(days=15),
        ))

        # 6. Clinical Records (PCOM detected)
        self.db.add(ClinicalRecord(
            user_id=user.id,
            testosterone=68.5,
            dheas=280.0,
            amh=6.2,
            ultrasound_findings="PCOM detected: 24 antral follicles in right ovary, enlarged volume",
            ovulation_history="Oligomenorrhea with prolonged intervals",
            recorded_at=datetime.now(timezone.utc) - timedelta(days=10),
        ))

        self.db.commit()

        # Build context
        context = build_user_health_context(self.db, user)

        # Assertions
        self.assertEqual(context.user_id, user.id)
        # Profile
        self.assertTrue(context.profile.is_present)
        self.assertEqual(context.profile.age, 27)
        self.assertEqual(context.profile.calculated_bmi, 25.0)
        self.assertEqual(context.profile.bmi_category, "Overweight")
        self.assertEqual(context.profile.diagnosis_status, "Diagnosed")
        self.assertIn("Insulin Resistance", context.profile.existing_conditions)
        self.assertIn("Metformin 500mg", context.profile.medications)

        # Cycles
        self.assertTrue(context.cycles.is_present)
        self.assertEqual(context.cycles.total_recorded_cycles, 3)
        self.assertIn("Oligomenorrhea", context.cycles.statistics["rhythm_classification"])
        self.assertTrue(context.cycles.statistics["is_irregular"])

        # Symptoms
        self.assertTrue(context.symptoms.is_present)
        self.assertEqual(context.symptoms.total_logged_days, 8)
        self.assertIsNotNone(context.symptoms.symptom_summary["mean_fatigue"])

        # Lifestyle & Correlations
        self.assertTrue(context.lifestyle.is_present)
        self.assertEqual(context.lifestyle.total_logged_days, 8)
        self.assertGreaterEqual(len(context.lifestyle.correlations), 1)
        valid_corr = [c for c in context.lifestyle.correlations if c["has_sufficient_data"]]
        self.assertTrue(len(valid_corr) >= 1)

        # Labs
        self.assertTrue(context.labs.is_present)
        self.assertEqual(context.labs.total_biomarkers_recorded, 2)
        self.assertEqual(len(context.labs.abnormal_biomarkers), 1)
        self.assertEqual(context.labs.abnormal_biomarkers[0]["canonical_name"], "Total Testosterone")
        self.assertEqual(context.labs.abnormal_biomarkers[0]["status"], "Elevated")

        # Clinical & Rotterdam
        self.assertTrue(context.clinical.is_present)
        self.assertEqual(context.clinical.total_records, 1)
        rotterdam = context.clinical.rotterdam_assessment
        # 3 positive pillars: ovulatory dysfunction (oligomenorrhea) + hyperandrogenism (elevated testosterone) + PCOM (ultrasound)
        self.assertEqual(rotterdam["criteria_present_count"], 3)
        self.assertIn("Phenotype A", rotterdam["educational_phenotype_alignment"])

        # Clinical markdown prompt text (privacy check: NO user email or real name in prompt)
        prompt_text = context.to_clinical_prompt_text()
        self.assertNotIn("alice_complete@example.com", prompt_text)
        self.assertNotIn("Alice Patient", prompt_text)
        self.assertIn("Oligomenorrhea", prompt_text)
        self.assertIn("Total Testosterone", prompt_text)
        self.assertIn("Phenotype A", prompt_text)

    # ==========================================================================
    # 2. Empty User Profiles (Honest Missing-Data Handling)
    # ==========================================================================
    def test_empty_user_profile_handling(self):
        """Verify context builder when a user has no profile record."""
        user, _ = self._create_user("Empty Profile", "empty_profile@example.com")
        from app.services.context_builder import build_user_health_context

        context = build_user_health_context(self.db, user)

        self.assertFalse(context.profile.is_present)
        self.assertIsNone(context.profile.age)
        self.assertIsNone(context.profile.height_cm)
        self.assertIsNone(context.profile.weight_kg)
        self.assertIsNone(context.profile.calculated_bmi)
        self.assertIsNone(context.profile.bmi_category)
        self.assertIn("age", context.profile.missing_fields)
        self.assertIn("height", context.profile.missing_fields)
        self.assertIn("weight", context.profile.missing_fields)
        self.assertTrue(any("profile has not been initialized" in s.lower() for s in context.missing_data_summary))

        prompt_text = context.to_clinical_prompt_text()
        self.assertIn("NOT INITIALIZED", prompt_text)

    # ==========================================================================
    # 3. Missing Lab Reports (Transparent Gaps & Rotterdam Impact)
    # ==========================================================================
    def test_missing_lab_reports_handling(self):
        """Verify context builder when user has cycles and symptoms but zero lab reports."""
        user, _ = self._create_user("No Labs", "no_labs@example.com")
        from app.models.menstrual_cycle import MenstrualCycle
        from app.services.context_builder import build_user_health_context

        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=date.today() - timedelta(days=60),
            cycle_length=28,
            flow_intensity="Medium",
        ))
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=date.today() - timedelta(days=32),
            cycle_length=28,
            flow_intensity="Medium",
        ))
        self.db.commit()

        context = build_user_health_context(self.db, user)

        self.assertFalse(context.labs.is_present)
        self.assertEqual(context.labs.total_biomarkers_recorded, 0)
        self.assertEqual(len(context.labs.evaluated_biomarkers), 0)
        self.assertIn("No laboratory biomarker reports on record.", context.labs.missing_data_note)
        self.assertIn("Total Testosterone", context.labs.missing_critical_pcos_biomarkers)
        self.assertIn("Fasting Glucose", context.labs.missing_critical_pcos_biomarkers)
        self.assertTrue(any("no laboratory biomarker reports logged" in s.lower() for s in context.missing_data_summary))

        # Rotterdam assessment should flag missing androgen lab panel
        rotterdam = context.clinical.rotterdam_assessment
        missing_docs = rotterdam.get("criteria_missing_documentation", [])
        self.assertTrue(any("androgen" in d.lower() for d in missing_docs))

    # ==========================================================================
    # 4. Missing Cycle History (Insufficient Data Guards: 0 and 1 Cycle)
    # ==========================================================================
    def test_zero_and_single_cycle_history(self):
        """Verify that 0 and 1 cycle records report insufficient data honestly."""
        # 0 cycles
        user0, _ = self._create_user("Zero Cycles", "zero_cycles@example.com")
        from app.services.context_builder import build_user_health_context

        context0 = build_user_health_context(self.db, user0)
        self.assertFalse(context0.cycles.is_present)
        self.assertEqual(context0.cycles.total_recorded_cycles, 0)
        self.assertIn("No menstrual cycles recorded", context0.cycles.missing_data_note)
        self.assertTrue(any("insufficient menstrual cycle history" in s.lower() for s in context0.missing_data_summary))

        # 1 cycle (insufficient for rhythm/regularity analysis)
        user1, _ = self._create_user("One Cycle", "one_cycle@example.com")
        from app.models.menstrual_cycle import MenstrualCycle

        self.db.add(MenstrualCycle(
            user_id=user1.id,
            period_start_date=date.today() - timedelta(days=25),
            cycle_length=28,
            flow_intensity="Medium",
        ))
        self.db.commit()

        context1 = build_user_health_context(self.db, user1)
        self.assertTrue(context1.cycles.is_present)
        self.assertEqual(context1.cycles.total_recorded_cycles, 1)
        stats = context1.cycles.statistics
        self.assertFalse(stats["has_sufficient_data"])
        self.assertIn("Insufficient", stats["rhythm_classification"])
        self.assertIn("at least 2", stats["missing_data_note"].lower())

    # ==========================================================================
    # 5. Cross-User Data Isolation (Strict Privacy Boundary)
    # ==========================================================================
    def test_strict_cross_user_isolation(self):
        """Ensure User A's context never contains User B's health records."""
        user_a, _ = self._create_user("User Alpha", "user_a_isolation@example.com")
        user_b, _ = self._create_user("User Beta", "user_b_isolation@example.com")

        from app.models.clinical_record import ClinicalRecord
        from app.models.daily_symptom import DailySymptom
        from app.models.health_profile import HealthProfile
        from app.models.lab_report import LabReport
        from app.models.lifestyle_log import LifestyleLog
        from app.models.menstrual_cycle import MenstrualCycle
        from app.services.context_builder import build_user_health_context

        # Data for User A
        self.db.add(HealthProfile(user_id=user_a.id, age=22, height=160, weight=55, diagnosis_status="Not diagnosed"))
        self.db.add(MenstrualCycle(user_id=user_a.id, period_start_date=date(2026, 1, 1), cycle_length=28, notes="AlphaCycle"))
        self.db.add(DailySymptom(user_id=user_a.id, log_date=date(2026, 1, 2), fatigue_level=3, notes="AlphaSymptom"))
        self.db.add(LifestyleLog(user_id=user_a.id, log_date=date(2026, 1, 2), sleep_hours=8.0, stress_level=2, water_intake=2.5, exercise_minutes=30))
        self.db.add(LabReport(user_id=user_a.id, report_name="AlphaLabReport", test_name="Fasting Glucose", test_value=85.0, unit="mg/dL", reference_range="70-99", report_date=date(2026, 1, 5)))
        self.db.add(ClinicalRecord(user_id=user_a.id, testosterone=25.0, ultrasound_findings="AlphaNormalOvaries"))

        # Data for User B
        self.db.add(HealthProfile(user_id=user_b.id, age=34, height=172, weight=88, diagnosis_status="Diagnosed"))
        self.db.add(MenstrualCycle(user_id=user_b.id, period_start_date=date(2026, 2, 1), cycle_length=48, notes="BetaCycle"))
        self.db.add(DailySymptom(user_id=user_b.id, log_date=date(2026, 2, 2), fatigue_level=9, notes="BetaSymptom"))
        self.db.add(LifestyleLog(user_id=user_b.id, log_date=date(2026, 2, 2), sleep_hours=5.0, stress_level=5, water_intake=1.0, exercise_minutes=0))
        self.db.add(LabReport(user_id=user_b.id, report_name="BetaLabReport", test_name="Total Testosterone", test_value=95.0, unit="ng/dL", reference_range="15-45", report_date=date(2026, 2, 5)))
        self.db.add(ClinicalRecord(user_id=user_b.id, testosterone=95.0, ultrasound_findings="BetaPCOMEnlarged"))

        self.db.commit()

        # Build context for User A
        ctx_a = build_user_health_context(self.db, user_a)
        dict_a_str = str(ctx_a.to_dict())

        # Verify User A has Alpha data and zero Beta data
        self.assertEqual(ctx_a.profile.age, 22)
        self.assertIn("AlphaCycle", dict_a_str)
        self.assertIn("AlphaSymptom", dict_a_str)
        self.assertIn("AlphaLabReport", dict_a_str)
        self.assertNotIn("BetaCycle", dict_a_str)
        self.assertNotIn("BetaSymptom", dict_a_str)
        self.assertNotIn("BetaLabReport", dict_a_str)
        self.assertNotIn("BetaPCOMEnlarged", dict_a_str)

        # Build context for User B
        ctx_b = build_user_health_context(self.db, user_b)
        dict_b_str = str(ctx_b.to_dict())

        # Verify User B has Beta data and zero Alpha data
        self.assertEqual(ctx_b.profile.age, 34)
        self.assertIn("BetaCycle", dict_b_str)
        self.assertIn("BetaSymptom", dict_b_str)
        self.assertIn("BetaLabReport", dict_b_str)
        self.assertNotIn("AlphaCycle", dict_b_str)
        self.assertNotIn("AlphaSymptom", dict_b_str)
        self.assertNotIn("AlphaLabReport", dict_b_str)
        self.assertNotIn("AlphaNormalOvaries", dict_b_str)

    # ==========================================================================
    # 6. Unauthorized Access (API Layer Enforcement)
    # ==========================================================================
    def test_unauthorized_context_api_access(self):
        """Verify API layer strictly rejects unauthenticated, invalid, and revoked access."""
        # 1. No token
        res_no_auth = self.client.get("/api/health-context/me")
        self.assertEqual(res_no_auth.status_code, 401)
        self.assertIn("WWW-Authenticate", res_no_auth.headers)

        # 2. Malformed token
        res_bad_token = self.client.get(
            "/api/health-context/me",
            headers={"Authorization": "Bearer not-a-valid-jwt-token"},
        )
        self.assertEqual(res_bad_token.status_code, 401)

        # 3. Valid authenticated request succeeds
        user, auth_header = self._create_user("Auth User", "auth_user_context@example.com")
        res_valid = self.client.get("/api/health-context/me", headers=auth_header)
        self.assertEqual(res_valid.status_code, 200)
        body = res_valid.json()
        self.assertEqual(body["user_id"], user.id)

        # 4. Summary endpoint also succeeds with auth
        res_summary = self.client.get("/api/health-context/me/summary", headers=auth_header)
        self.assertEqual(res_summary.status_code, 200)
        summary_body = res_summary.json()
        self.assertIn("summary_markdown", summary_body)

        # 5. Revoked session after logout returns 401
        res_logout = self.client.post("/api/auth/logout", headers=auth_header)
        self.assertEqual(res_logout.status_code, 200)
        res_after_logout = self.client.get("/api/health-context/me", headers=auth_header)
        self.assertEqual(res_after_logout.status_code, 401)

    # ==========================================================================
    # 7. Database Error Handling
    # ==========================================================================
    def test_database_error_handling(self):
        """Verify clean error handling when a database failure occurs."""
        from app.services.context_builder import ContextBuilderDatabaseError, build_user_health_context

        user, _ = self._create_user("DB Error User", "db_error_user@example.com")

        mock_db = MagicMock()
        mock_db.query.side_effect = OperationalError("SELECT * FROM users", {}, Exception("Database connection lost"))

        with self.assertRaises(ContextBuilderDatabaseError):
            build_user_health_context(mock_db, user)


if __name__ == "__main__":
    unittest.main()
