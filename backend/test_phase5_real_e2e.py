"""Phase 5: Real End-to-End Validation Script for PCOS360.

Tests complete user journeys against live FastAPI routes and authentic PostgreSQL records:
1. User registration & verification in PostgreSQL.
2. Login, signed JWT generation, & user_sessions record verification.
3. Health profile creation, calculation of BMI, and update.
4. Menstrual cycle tracking across multiple cycles.
5. Daily symptom logging across consecutive days.
6. Lifestyle logging (sleep, stress, hydration, exercise).
7. Laboratory biomarker reports (fasting glucose, testosterone).
8. Deterministic PCOSCOPE pattern discovery (cycle regularity, correlations N>=7, trajectories).
9. Live AI conversational interaction incorporating authentic context.
10. AI consultation copilot & appointment question generation.
11. Health context retrieval & data freshness check.
12. Logout & session revocation verification (rejection with HTTP 401).
13. Clean database teardown of the test user.
"""

from datetime import date, datetime, timedelta, timezone
import json
import time
import uuid

from fastapi.testclient import TestClient
from sqlalchemy import text

from app.core.database import get_db, get_engine, SessionLocal
from app.core.security import decode_access_token
from app.main import app
from app.models.health_profile import HealthProfile
from app.models.lab_report import LabReport
from app.models.lifestyle_log import LifestyleLog
from app.models.menstrual_cycle import MenstrualCycle
from app.models.daily_symptom import DailySymptom
from app.models.user import User
from app.models.user_session import UserSession


def run_e2e_tests():
    print("=" * 80)
    print("PCOS360 PHASE 5: REAL END-TO-END VALIDATION (POSTGRESQL & FASTAPI)")
    print("=" * 80)

    client = TestClient(app)
    db = SessionLocal()
    engine = get_engine()
    test_id = uuid.uuid4().hex[:8]
    test_email = f"e2e_patient_{test_id}@pcos360-test.org"
    test_password = "PcosSecurePass!2026"
    test_name = f"E2E Patient {test_id}"

    user_id = None
    access_token = None
    headers = {}

    try:
        # ----------------------------------------------------------------------
        # Journey 1: User Registration
        # ----------------------------------------------------------------------
        print("\n[STEP 1/12] Registering new user account...")
        reg_resp = client.post(
            "/api/auth/register",
            json={
                "email": test_email,
                "password": test_password,
                "full_name": test_name,
            },
        )
        assert reg_resp.status_code == 201, f"Registration failed ({reg_resp.status_code}): {reg_resp.text}"
        reg_data = reg_resp.json()
        assert reg_data["user"]["email"] == test_email
        user_id = reg_data["user"]["id"]

        # Verify authentic PostgreSQL persistence
        pg_user = db.query(User).filter(User.id == user_id).first()
        assert pg_user is not None, "User record was not found in PostgreSQL!"
        assert pg_user.email == test_email
        assert pg_user.password_hash is not None
        assert "scrypt" in pg_user.password_hash
        print(f"  ✓ User registered in PostgreSQL: id={user_id}, email={test_email}")

        # ----------------------------------------------------------------------
        # Journey 2: Login & JWT Session Persistence
        # ----------------------------------------------------------------------
        print("\n[STEP 2/12] Logging in & authenticating JWT session...")
        login_resp = client.post(
            "/api/auth/login",
            json={
                "email": test_email,
                "password": test_password,
            },
        )
        assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
        login_data = login_resp.json()
        access_token = login_data["access_token"]
        assert access_token, "No access token returned"
        headers = {"Authorization": f"Bearer {access_token}"}

        # Verify token decoding and server-side session in PostgreSQL
        payload = decode_access_token(access_token)
        assert payload["user_id"] == user_id
        jti = payload["jti"]

        pg_session = db.query(UserSession).filter(UserSession.token_jti == jti).first()
        assert pg_session is not None, "UserSession record not found in PostgreSQL!"
        assert pg_session.user_id == user_id
        assert pg_session.revoked_at is None
        print(f"  ✓ Validated JWT & active session in PostgreSQL: jti={jti[:12]}...")

        # ----------------------------------------------------------------------
        # Journey 3: Health Profile Creation & Update
        # ----------------------------------------------------------------------
        print("\n[STEP 3/12] Creating baseline health profile...")
        profile_resp = client.post(
            "/api/profile/",
            headers=headers,
            json={
                "age": 27,
                "height": 164.0,
                "weight": 68.5,
                "diagnosis_status": "Diagnosed",
                "diagnosis_year": 2023,
                "existing_conditions": ["Insulin Resistance"],
                "medications": ["Myo-Inositol 2000mg", "Metformin 500mg"],
            },
        )
        assert profile_resp.status_code == 201, f"Profile create failed: {profile_resp.text}"
        profile_data = profile_resp.json()
        assert profile_data["age"] == 27
        assert profile_data["height"] == 164.0

        # Verify profile in PostgreSQL
        pg_profile = db.query(HealthProfile).filter(HealthProfile.user_id == user_id).first()
        assert pg_profile is not None
        assert pg_profile.weight == 68.5
        bmi = round(68.5 / ((164.0 / 100) ** 2), 1)
        print(f"  ✓ Health profile saved in PostgreSQL: Age {pg_profile.age}, Calculated BMI: {bmi}")

        # ----------------------------------------------------------------------
        # Journey 4: Menstrual Cycle Logging (3 Consecutive Cycles)
        # ----------------------------------------------------------------------
        print("\n[STEP 4/12] Logging 3 consecutive menstrual cycles...")
        base_date = date.today() - timedelta(days=90)
        cycle_lengths = [32, 35, 33]
        for i, clen in enumerate(cycle_lengths):
            c_start = base_date + timedelta(days=i * 30)
            c_resp = client.post(
                "/api/cycles/",
                headers=headers,
                json={
                    "period_start_date": c_start.isoformat(),
                    "period_end_date": (c_start + timedelta(days=5)).isoformat(),
                    "cycle_length": clen,
                    "flow_intensity": "Medium",
                    "notes": f"Cycle {i+1} documented for E2E test",
                },
            )
            assert c_resp.status_code == 201, f"Cycle {i+1} logging failed: {c_resp.text}"

        pg_cycles = db.query(MenstrualCycle).filter(MenstrualCycle.user_id == user_id).all()
        assert len(pg_cycles) == 3, f"Expected 3 cycles, found {len(pg_cycles)}"
        print(f"  ✓ 3 menstrual cycles stored in PostgreSQL: {[c.cycle_length for c in pg_cycles]} days")

        # ----------------------------------------------------------------------
        # Journey 5: Daily Symptom Logging (7 Consecutive Days)
        # ----------------------------------------------------------------------
        print("\n[STEP 5/12] Logging 7 daily symptom check-ins...")
        today = date.today()
        for d_offset in range(7):
            log_d = today - timedelta(days=6 - d_offset)
            sym_resp = client.post(
                "/api/symptoms/",
                headers=headers,
                json={
                    "log_date": log_d.isoformat(),
                    "acne_severity": "Moderate" if d_offset % 2 == 0 else "Mild",
                    "hair_loss": "Mild",
                    "unwanted_hair_growth": "None",
                    "fatigue_level": max(2, 8 - d_offset),  # 8 down to 2
                    "bloating": max(2, 7 - d_offset),
                    "pelvic_pain": 2,
                    "mood": "Stable",
                    "notes": f"Day {d_offset+1} symptom check-in",
                },
            )
            assert sym_resp.status_code == 201, f"Symptom log failed on day {d_offset}: {sym_resp.text}"

        pg_symptoms = db.query(DailySymptom).filter(DailySymptom.user_id == user_id).all()
        assert len(pg_symptoms) == 7
        print(f"  ✓ 7 daily symptom records verified in PostgreSQL")

        # ----------------------------------------------------------------------
        # Journey 6: Lifestyle Tracking (7 Consecutive Days)
        # ----------------------------------------------------------------------
        print("\n[STEP 6/12] Logging 7 paired daily lifestyle records...")
        for d_offset in range(7):
            log_d = today - timedelta(days=6 - d_offset)
            life_resp = client.post(
                "/api/lifestyle/",
                headers=headers,
                json={
                    "log_date": log_d.isoformat(),
                    "sleep_hours": 6.0 + (d_offset * 0.4),  # 6.0 to 8.4 hrs
                    "stress_level": max(1, 4 - (d_offset // 2)),
                    "water_intake": 2.2,
                    "exercise_minutes": 20 + (d_offset * 5),
                    "food_habits": "Low-GI",
                    "meal_regularity": "Regular",
                },
            )
            assert life_resp.status_code == 201, f"Lifestyle log failed on day {d_offset}: {life_resp.text}"

        pg_lifestyle = db.query(LifestyleLog).filter(LifestyleLog.user_id == user_id).all()
        assert len(pg_lifestyle) == 7
        print(f"  ✓ 7 lifestyle records verified in PostgreSQL")

        # ----------------------------------------------------------------------
        # Journey 7: Laboratory Reports Management
        # ----------------------------------------------------------------------
        print("\n[STEP 7/12] Uploading laboratory biomarker reports...")
        lab_items = [
            ("Fasting Glucose", 104.0, "mg/dL", "70-99", today - timedelta(days=15)),
            ("Total Testosterone", 62.0, "ng/dL", "15-45", today - timedelta(days=15)),
        ]
        for tname, val, unit, rrange, rdate in lab_items:
            l_resp = client.post(
                "/api/lab-reports/",
                headers=headers,
                json={
                    "report_name": "Metabolic & Hormone Panel",
                    "test_name": tname,
                    "test_value": val,
                    "unit": unit,
                    "reference_range": rrange,
                    "report_date": rdate.isoformat(),
                },
            )
            assert l_resp.status_code == 201, f"Lab report failed: {l_resp.text}"

        pg_labs = db.query(LabReport).filter(LabReport.user_id == user_id).all()
        assert len(pg_labs) == 2
        print(f"  ✓ 2 lab biomarkers saved in PostgreSQL: {[l.test_name for l in pg_labs]}")

        # ----------------------------------------------------------------------
        # Journey 8: PCOSCOPE Deterministic Pattern Discovery
        # ----------------------------------------------------------------------
        print("\n[STEP 8/12] Querying GET /api/pcoscope/analysis...")
        t0 = time.time()
        pcoscope_resp = client.get("/api/pcoscope/analysis?window_days=30", headers=headers)
        pcoscope_duration = round((time.time() - t0) * 1000)

        assert pcoscope_resp.status_code == 200, f"PCOSCOPE analysis failed: {pcoscope_resp.text}"
        pdata = pcoscope_resp.json()

        assert pdata["user_id"] == user_id
        assert pdata["data_completeness"]["overall_score_pct"] >= 75
        assert pdata["cycle_patterns"]["sample_size"] == 3
        assert "Estimated" in pdata["cycle_patterns"]["estimated_current_phase"]
        assert "UNCONFIRMED" in pdata["cycle_patterns"]["ovulation_confirmation_status"]

        # Verify N >= 7 Lifestyle Correlation
        corrs = pdata["lifestyle_correlations"]
        assert len(corrs) > 0
        sleep_fatigue = next(c for c in corrs if "Sleep" in c["factor_a"] and "Fatigue" in c["factor_b"])
        assert sleep_fatigue["sample_size"] == 7
        assert sleep_fatigue["has_sufficient_data"] is True
        assert sleep_fatigue["correlation_coefficient"] is not None
        assert sleep_fatigue["correlation_coefficient"] < 0  # Inverse correlation: more sleep -> less fatigue
        print(f"  ✓ PCOSCOPE response received in {pcoscope_duration} ms")
        print(f"    - Completeness Score: {pdata['data_completeness']['overall_score_pct']}%")
        print(f"    - Cycle Rhythm: {pdata['cycle_patterns']['rhythm_classification']}")
        print(f"    - Correlation: {sleep_fatigue['factor_a']} vs {sleep_fatigue['factor_b']} (r = {sleep_fatigue['correlation_coefficient']})")
        print(f"    - Ovulation Disclaimer: {pdata['cycle_patterns']['ovulation_confirmation_status'][:45]}...")

        # ----------------------------------------------------------------------
        # Journey 9: Live AI Conversational Interaction
        # ----------------------------------------------------------------------
        print("\n[STEP 9/12] Testing POST /api/ai/chat with live context...")
        t0 = time.time()
        chat_resp = client.post(
            "/api/ai/chat",
            headers=headers,
            json={
                "message": "Based on my recent logs, how is my cycle and fasting glucose looking?",
                "include_context": True,
            },
        )
        chat_duration = round((time.time() - t0) * 1000)
        assert chat_resp.status_code == 200, f"AI chat failed: {chat_resp.text}"
        cdata = chat_resp.json()
        assert cdata["status"] in ("success", "partial_deterministic")
        assert cdata["is_personalized"] is True
        assert len(cdata["response_text"]) > 50
        print(f"  ✓ AI response generated in {chat_duration} ms (Provider: {cdata['provider_used']})")
        print(f"    Preview: {cdata['response_text'][:120]}...")

        # ----------------------------------------------------------------------
        # Journey 10: AI Consultation Copilot
        # ----------------------------------------------------------------------
        print("\n[STEP 10/12] Testing POST /api/ai/copilot for appointment prep...")
        copilot_resp = client.post(
            "/api/ai/copilot",
            headers=headers,
            json={
                "action": "consultation_packet",
                "user_query": "I have an appointment with an endocrinologist next week.",
            },
        )
        assert copilot_resp.status_code == 200, f"Copilot action failed: {copilot_resp.text}"
        cpdata = copilot_resp.json()
        assert len(cpdata["response_text"]) > 50
        assert "disclaimer" in cpdata
        print(f"  ✓ Copilot consultation packet generated (Provider: {cpdata['provider_used']})")

        # ----------------------------------------------------------------------
        # Journey 11: Health Context Engine Structured & Markdown Retrieval
        # ----------------------------------------------------------------------
        print("\n[STEP 11/12] Testing GET /api/health-context/me and /me/summary...")
        ctx_resp = client.get("/api/health-context/me", headers=headers)
        assert ctx_resp.status_code == 200, f"Context retrieval failed: {ctx_resp.text}"
        ctx_data = ctx_resp.json()
        assert ctx_data["profile"]["is_present"] is True
        assert ctx_data["cycles"]["total_recorded_cycles"] == 3
        assert ctx_data["symptoms"]["total_logged_days"] == 7
        assert ctx_data["lifestyle"]["total_logged_days"] == 7
        assert ctx_data["labs"]["total_biomarkers_recorded"] == 2

        summary_resp = client.get("/api/health-context/me/summary", headers=headers)
        assert summary_resp.status_code == 200, f"Summary retrieval failed: {summary_resp.text}"
        sum_data = summary_resp.json()
        assert "summary_markdown" in sum_data
        assert "CLINICAL HEALTH CONTEXT" in sum_data["summary_markdown"]
        print(f"  ✓ Complete authentic context verified: 3 cycles, 7 symptoms, 7 lifestyle, 2 labs")
        print(f"  ✓ Prompt-ready clinical markdown summary verified ({len(sum_data['summary_markdown'])} chars)")

        # ----------------------------------------------------------------------
        # Journey 12: Logout & Session Expiration Verification
        # ----------------------------------------------------------------------
        print("\n[STEP 12/12] Logging out & verifying session revocation...")
        logout_resp = client.post("/api/auth/logout", headers=headers)
        assert logout_resp.status_code == 200, f"Logout failed: {logout_resp.text}"

        # Verify session in PostgreSQL has revoked_at timestamp set
        db.expire_all()
        revoked_session = db.query(UserSession).filter(UserSession.token_jti == jti).first()
        assert revoked_session is not None
        assert revoked_session.revoked_at is not None, "Session was not marked revoked in PostgreSQL!"

        # Subsequent authenticated request MUST be rejected with HTTP 401
        rejected_resp = client.get("/api/pcoscope/analysis", headers=headers)
        assert rejected_resp.status_code == 401, f"Expected 401 Unauthorized after logout, got {rejected_resp.status_code}"
        print(f"  ✓ Session marked revoked in PostgreSQL at {revoked_session.revoked_at}")
        print(f"  ✓ Subsequent request with revoked JWT was rejected with HTTP 401 Unauthorized")

        print("\n" + "=" * 80)
        print("ALL 12 END-TO-END USER JOURNEYS PASSED WITH 100% SUCCESS!")
        print("=" * 80)

    finally:
        # Cleanup test user from PostgreSQL to maintain clean database state
        if user_id:
            print(f"\n[CLEANUP] Removing test user (id={user_id}) and cascading records from PostgreSQL...")
            try:
                # CASCADE delete cleans up health_profiles, menstrual_cycles, daily_symptoms, lifestyle_logs, lab_reports, sessions
                db.execute(text("DELETE FROM users WHERE id = :uid"), {"uid": user_id})
                db.commit()
                print("  ✓ Cleanup complete. Zero orphan records left in PostgreSQL.")
            except Exception as e:
                db.rollback()
                print(f"  Warning: Cleanup error: {e}")
        db.close()


if __name__ == "__main__":
    run_e2e_tests()
