"""Comprehensive unit and integration tests for PCOSCOPE Engine (Phase 4).

Tests:
1. Cycle pattern analysis with regular, irregular, and empty histories.
2. Estimated phase labeling and mandatory unconfirmed ovulation status disclaimers.
3. Symptom clustering, prevalence %, severity score mapping, and co-occurrence detection.
4. Lifestyle correlation matrix with strict N >= 7 data-quality threshold.
5. Refusal to assert correlation when N < 7 with clear warning.
6. Longitudinal biomarker trajectory analysis across sequential lab reports.
7. Clinical care gaps identification and record completeness score calculation.
8. Cross-user data isolation (User A vs User B).
9. Full FastAPI route integration tests for GET /api/pcoscope/analysis and /insights.
10. Deterministic narrative fallback when external AI providers are unavailable.
"""

from datetime import date, datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import get_current_user
from app.core.database import Base, get_db
from app.core.security import hash_password
from app.main import app
from app.models.clinical_record import ClinicalRecord
from app.models.daily_symptom import DailySymptom
from app.models.health_profile import HealthProfile
from app.models.lab_report import LabReport
from app.models.lifestyle_log import LifestyleLog
from app.models.menstrual_cycle import MenstrualCycle
from app.models.user import User
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


@pytest.fixture
def in_memory_db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = TestingSession()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def seeded_users(in_memory_db):
    user_a = User(
        email="patient_a@example.com",
        password_hash=hash_password("Password123!"),
        full_name="Patient Alpha",
        is_active=True,
    )
    user_b = User(
        email="patient_b@example.com",
        password_hash=hash_password("Password123!"),
        full_name="Patient Beta",
        is_active=True,
    )
    in_memory_db.add_all([user_a, user_b])
    in_memory_db.commit()
    in_memory_db.refresh(user_a)
    in_memory_db.refresh(user_b)
    return user_a, user_b


# ==============================================================================
# 1. Cycle Pattern Discovery Tests
# ==============================================================================

def test_cycle_patterns_empty():
    """Verify empty cycles list returns zero sample size, clean labels, and unconfirmed ovulation status."""
    res = analyze_cycle_patterns([])
    assert res.sample_size == 0
    assert res.has_sufficient_data is False
    assert res.mean_length_days is None
    assert res.rhythm_classification == "No Cycles Logged"
    assert "No Menstrual Cycles Logged" in res.estimated_current_phase
    assert "UNCONFIRMED" in res.ovulation_confirmation_status


def test_cycle_patterns_regular():
    """Verify regular 28-day cycles are correctly classified under Monash 2023 with estimated phase."""
    c1 = MenstrualCycle(period_start_date=date(2026, 1, 1), cycle_length=28)
    c2 = MenstrualCycle(period_start_date=date(2026, 1, 29), cycle_length=28)
    c3 = MenstrualCycle(period_start_date=date(2026, 2, 26), cycle_length=29)

    res = analyze_cycle_patterns([c1, c2, c3])
    assert res.sample_size == 3
    assert res.has_sufficient_data is True
    assert res.mean_length_days == pytest.approx(28.3, 0.1)
    assert "Regular" in res.rhythm_classification
    assert res.is_irregular is False
    assert "Estimated" in res.estimated_current_phase
    assert "UNCONFIRMED" in res.ovulation_confirmation_status
    assert res.next_period_estimated is not None


def test_cycle_patterns_irregular():
    """Verify cycles > 35 days are classified as Irregular / Oligomenorrhea under Monash 2023."""
    c1 = MenstrualCycle(period_start_date=date(2025, 9, 1), cycle_length=38)
    c2 = MenstrualCycle(period_start_date=date(2025, 10, 10), cycle_length=44)
    c3 = MenstrualCycle(period_start_date=date(2025, 11, 25), cycle_length=42)

    res = analyze_cycle_patterns([c1, c2, c3])
    assert res.sample_size == 3
    assert res.is_irregular is True
    assert "Oligomenorrhea" in res.rhythm_classification or "Irregular" in res.rhythm_classification
    assert "Monash 2023" in res.guideline_reference


# ==============================================================================
# 2. Symptom Clustering & Temporal Analysis Tests
# ==============================================================================

def test_symptom_trends_clustering():
    """Verify symptom frequencies, severity averages, and co-occurrences are accurately computed."""
    today = date.today()
    symptoms = [
        DailySymptom(
            log_date=today - timedelta(days=i),
            fatigue_level=7 if i % 2 == 0 else 3,
            bloating=6 if i % 2 == 0 else 2,
            acne_severity="Moderate" if i % 3 == 0 else "Mild",
        )
        for i in range(10)
    ]

    analysis = analyze_symptom_trends(symptoms=symptoms, lifestyle_logs=[], window_days=30)
    assert analysis.total_logged_days == 10
    assert len(analysis.top_clusters) >= 3

    # Check fatigue cluster
    fatigue_cluster = next((c for c in analysis.top_clusters if c.symptom_key == "fatigue"), None)
    assert fatigue_cluster is not None
    assert fatigue_cluster.occurrences_count == 10
    assert fatigue_cluster.prevalence_pct == 100.0
    assert fatigue_cluster.average_severity == 5.0

    # Co-occurrence should detect Bloating and Acne
    assert "Bloating" in fatigue_cluster.co_occurring_symptoms or "Acne" in fatigue_cluster.co_occurring_symptoms


# ==============================================================================
# 3. Lifestyle Correlation Tests (N >= 7 Data-Quality Guard)
# ==============================================================================

def test_lifestyle_correlations_insufficient_sample_size():
    """Verify N < 7 strictly refuses to assert correlation and returns clear data-quality warning."""
    today = date.today()
    # Seed only 4 paired days (N = 4 < 7)
    symptoms = [DailySymptom(log_date=today - timedelta(days=i), fatigue_level=6) for i in range(4)]
    lifestyle = [
        LifestyleLog(
            log_date=today - timedelta(days=i),
            sleep_hours=7.0,
            stress_level=3,
            water_intake=2.0,
            exercise_minutes=20,
        )
        for i in range(4)
    ]

    corrs = analyze_lifestyle_correlations(symptoms=symptoms, lifestyle_logs=lifestyle, min_sample_size=7)
    assert len(corrs) > 0

    sleep_fatigue = next(c for c in corrs if "Sleep" in c.factor_a and "Fatigue" in c.factor_b)
    assert sleep_fatigue.sample_size == 4
    assert sleep_fatigue.has_sufficient_data is False
    assert sleep_fatigue.correlation_coefficient is None
    assert "Data-quality threshold not met" in sleep_fatigue.significance_warning
    assert "N=4 < 7" in sleep_fatigue.significance_warning


def test_lifestyle_correlations_sufficient_sample_size():
    """Verify N >= 7 calculates Pearson r and attaches mandatory observational caveats."""
    today = date.today()
    # Seed 10 paired days with inverse relationship between sleep and fatigue
    symptoms = []
    lifestyle = []
    for i in range(10):
        d = today - timedelta(days=i)
        sleep = 5.0 + (i * 0.4)  # 5.0 to 8.6 hours
        fatigue = max(1, round(10.0 - (i * 0.8)))  # 10 down to 3
        symptoms.append(DailySymptom(log_date=d, fatigue_level=fatigue))
        lifestyle.append(
            LifestyleLog(
                log_date=d,
                sleep_hours=sleep,
                stress_level=3,
                water_intake=2.0,
                exercise_minutes=30,
            )
        )

    corrs = analyze_lifestyle_correlations(symptoms=symptoms, lifestyle_logs=lifestyle, min_sample_size=7)
    sleep_fatigue = next(c for c in corrs if "Sleep" in c.factor_a and "Fatigue" in c.factor_b)

    assert sleep_fatigue.sample_size == 10
    assert sleep_fatigue.has_sufficient_data is True
    assert sleep_fatigue.correlation_coefficient is not None
    assert sleep_fatigue.correlation_coefficient < -0.8  # Strong negative correlation
    assert sleep_fatigue.direction == "Negative"
    assert sleep_fatigue.strength == "Strong"
    assert "meets the minimum preliminary data-quality threshold (N>=7)" in sleep_fatigue.significance_warning
    assert "does NOT establish medical causation" in sleep_fatigue.significance_warning
    assert "Observational correlation only" in sleep_fatigue.caveat


# ==============================================================================
# 4. Biomarker Trajectories & Care Gaps Tests
# ==============================================================================

def test_biomarker_trajectories():
    """Verify sequential lab reports build chronological histories with trend directions."""
    r1 = LabReport(
        test_name="Fasting Blood Sugar",
        test_value=115.0,
        unit="mg/dL",
        reference_range="70-99",
        report_date=date(2025, 6, 1),
    )
    r2 = LabReport(
        test_name="Fasting Glucose",
        test_value=94.0,
        unit="mg/dL",
        reference_range="70-99",
        report_date=date(2025, 12, 1),
    )

    trajectories = analyze_biomarker_trajectories([r1, r2])
    assert len(trajectories) == 1
    t = trajectories[0]
    assert t.canonical_name == "fasting_glucose"
    assert t.datapoints_count == 2
    assert t.latest_value == 94.0
    assert t.latest_status == "Normal"
    assert t.trajectory_trend == "Improving"  # Glucose decreased from 115 to 94
    assert len(t.history) == 2


def test_care_gaps_and_completeness():
    """Verify missing glycemic and androgen panels are flagged as clinical care gaps."""
    profile = HealthProfile(age=26, height=165.0, weight=68.0)
    gaps = evaluate_care_gaps(
        profile=profile,
        cycles=[],
        symptoms=[],
        lifestyle_logs=[],
        lab_reports=[],
        clinical_records=[],
    )
    gap_titles = [g.title for g in gaps]
    assert any("Glycemic" in t for t in gap_titles)
    assert any("Androgen" in t for t in gap_titles)
    assert any("Cycles" in t for t in gap_titles)

    completeness = calculate_data_completeness(
        profile=profile,
        cycles=[],
        symptoms=[],
        lifestyle_logs=[],
        lab_reports=[],
    )
    assert completeness.overall_score_pct == 20  # Only profile is initialized (20 pts)
    assert completeness.profile_initialized is True
    assert len(completeness.missing_critical_elements) > 0


# ==============================================================================
# 5. User Data Isolation Test
# ==============================================================================

def test_cross_user_data_isolation(in_memory_db, seeded_users):
    """Verify User A's health records are never included in User B's PCOSCOPE analysis."""
    user_a, user_b = seeded_users

    # Seed User A with 3 cycles and 7 symptoms
    today = date.today()
    for i in range(3):
        in_memory_db.add(
            MenstrualCycle(
                user_id=user_a.id,
                period_start_date=today - timedelta(days=90 - (i * 30)),
                cycle_length=30,
            )
        )
    for i in range(7):
        in_memory_db.add(
            DailySymptom(
                user_id=user_a.id,
                log_date=today - timedelta(days=i),
                fatigue_level=8,
            )
        )
    in_memory_db.commit()

    # Run analysis for User A
    analysis_a = run_pcoscope_analysis(db=in_memory_db, user=user_a)
    assert analysis_a.data_completeness.cycles_logged_count == 3
    assert analysis_a.cycle_patterns.sample_size == 3
    assert analysis_a.symptom_trends.total_logged_days == 7

    # Run analysis for User B (must have 0 records)
    analysis_b = run_pcoscope_analysis(db=in_memory_db, user=user_b)
    assert analysis_b.data_completeness.cycles_logged_count == 0
    assert analysis_b.cycle_patterns.sample_size == 0
    assert analysis_b.symptom_trends.total_logged_days == 0
    assert analysis_b.user_id == user_b.id


# ==============================================================================
# 6. PCOSCOPE API Routes & Deterministic Fallback Tests
# ==============================================================================

def test_pcoscope_analysis_api_endpoint(in_memory_db, seeded_users):
    """Test authenticated GET /api/pcoscope/analysis endpoint."""
    user_a, _ = seeded_users

    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        client = TestClient(app)
        resp = client.get("/api/pcoscope/analysis")
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_id"] == user_a.id
        assert "cycle_patterns" in data
        assert "symptom_trends" in data
        assert "lifestyle_correlations" in data
        assert "data_completeness" in data
        assert "disclaimer" in data
    finally:
        app.dependency_overrides.clear()


def test_pcoscope_insights_deterministic_fallback(in_memory_db, seeded_users):
    """Test GET /api/pcoscope/insights gracefully degrades to deterministic narrative when AI providers fail."""
    user_a, _ = seeded_users

    def override_get_db():
        try:
            yield in_memory_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = lambda: user_a
    try:
        # Patch AI dispatch to simulate provider outage
        with patch("app.services.pcoscope_engine._dispatch_ai_request", side_effect=Exception("API Outage")):
            client = TestClient(app)
            resp = client.get("/api/pcoscope/insights")
            assert resp.status_code == 200
            data = resp.json()
            assert data["is_ai_generated"] is False
            assert data["provider_used"] == "deterministic_fallback"
            assert "Deterministic Mode" in data["narrative_summary"]
            assert len(data["doctor_discussion_points"]) > 0
    finally:
        app.dependency_overrides.clear()
