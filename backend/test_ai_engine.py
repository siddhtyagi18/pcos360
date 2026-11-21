"""Comprehensive test suite for Phase 3: Centralized AI Intelligence Engine.

Covers:
1. Gemini primary provider integration (mocked API).
2. Groq secondary provider fallback when Gemini fails.
3. Provider timeout handling with controlled retries.
4. Invalid API key handling (401/400 client error detection).
5. Missing user health data (honest missing indicators, zero fabrication).
6. Personalized response generation (authentic context verification).
7. Cross-user data isolation (zero context leakage).
8. Medical safety and emergency escalation (acute red-flag detection).
9. Malformed AI responses (empty candidates, missing parts).
10. Complete provider failure (graceful deterministic fallback).
11. Live API smoke test (conditional on live GEMINI_API_KEY).
"""

from datetime import date, datetime, timedelta, timezone
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient
import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

os.environ.setdefault("SECRET_KEY", "test-only-ephemeral-secret-key-at-least-32-chars")


class TestAIEngine(unittest.TestCase):
    """Automated tests for Phase 3: Centralized AI Intelligence Engine."""

    @classmethod
    def setUpClass(cls):
        fd, cls.db_path = tempfile.mkstemp(prefix="pcos360_ai_test_", suffix=".db")
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
    # 1. Primary Gemini Integration (Mocked)
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GEMINI_MODEL", "gemini-2.5-flash")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine.httpx.Client")
    def test_gemini_integration_mocked(self, mock_client_cls):
        """Verify successful generation using the primary Google Gemini API."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {"text": "Based on your cycle history, your 38-day cycles align with oligomenorrhea as defined by Monash 2023 guidelines."}
                        ]
                    }
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        user, auth_header = self._create_user("Gemini User", "gemini_user@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "Can you explain why my periods are delayed?"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200, res.text)
        body = res.json()

        self.assertEqual(body["status"], "success")
        self.assertEqual(body["provider_used"], "gemini")
        self.assertEqual(body["model_used"], "gemini-2.5-flash")
        self.assertIn("oligomenorrhea", body["response_text"].lower())
        self.assertGreaterEqual(len(body["citations"]), 1)
        self.assertIn("Educational decision-support only", body["disclaimer"])

    # ==========================================================================
    # 2. Secondary Groq Fallback
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "test-groq-key")
    @patch.object(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine._call_groq_api")
    @patch("app.services.ai_engine._call_gemini_api")
    def test_groq_fallback_when_gemini_fails(self, mock_gemini, mock_groq):
        """Verify seamless fallback to Groq when Gemini raises a service error."""
        mock_gemini.side_effect = httpx.HTTPStatusError("500 Internal Error", request=MagicMock(), response=MagicMock(status_code=500))
        mock_groq.return_value = "Groq response: According to Rotterdam criteria, cycle variability is one pillar of PCOS."

        user, auth_header = self._create_user("Groq Fallback User", "groq_user@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "What is the Rotterdam criteria?"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(body["status"], "success")
        self.assertEqual(body["provider_used"], "groq")
        self.assertEqual(body["model_used"], "llama-3.3-70b-versatile")
        self.assertIn("Groq response", body["response_text"])

    # ==========================================================================
    # 3. Provider Timeout Handling
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "test-groq-key")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine._call_groq_api")
    @patch("app.services.ai_engine._call_gemini_api")
    def test_provider_timeout_handling(self, mock_gemini, mock_groq):
        """Verify engine gracefully falls back to deterministic report on network timeout."""
        mock_gemini.side_effect = httpx.TimeoutException("Gemini timed out")
        mock_groq.side_effect = httpx.TimeoutException("Groq timed out")

        user, auth_header = self._create_user("Timeout User", "timeout_user@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "Tell me about my PCOS risk."},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(body["status"], "partial_deterministic")
        self.assertEqual(body["provider_used"], "deterministic_fallback")
        self.assertIn("Deterministic Clinical Mode Active", body["response_text"])

    # ==========================================================================
    # 4. Invalid API Key Handling (Client Error)
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "invalid-key")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 3)
    @patch("app.services.ai_engine._call_gemini_api")
    def test_invalid_api_key_handling(self, mock_gemini):
        """Verify client 401/400 errors immediately trigger fallback without infinite retries."""
        mock_gemini.side_effect = httpx.HTTPStatusError("401 Unauthorized", request=MagicMock(), response=MagicMock(status_code=401))

        user, auth_header = self._create_user("Invalid Key User", "invalid_key_user@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "Hello AI"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(body["status"], "partial_deterministic")
        self.assertEqual(body["provider_used"], "deterministic_fallback")

    # ==========================================================================
    # 5. Missing User Health Data
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine._call_gemini_api")
    def test_missing_user_health_data_handling(self, mock_gemini):
        """Verify AI prompt transparently reports missing data for a brand new user."""
        captured_prompt = {}

        def capture_call(prompt, **kwargs):
            captured_prompt["prompt"] = prompt
            return "I notice you have not logged any cycles or laboratory tests yet."

        mock_gemini.side_effect = capture_call

        user, auth_header = self._create_user("Brand New User", "brand_new_ai@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "What should I do first for my PCOS?"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertIn("prompt", captured_prompt)
        prompt_content = captured_prompt["prompt"]
        self.assertIn("NOT INITIALIZED", prompt_content)
        self.assertTrue("no menstrual cycles" in prompt_content.lower() or "no cycles logged" in prompt_content.lower())
        self.assertTrue("no laboratory" in prompt_content.lower())
        self.assertGreaterEqual(len(body["missing_data_noted"]), 2)

    # ==========================================================================
    # 6. Personalized Response Generation
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine._call_gemini_api")
    def test_personalized_response_generation(self, mock_gemini):
        """Verify prompt sent to LLM contains authentic patient metrics."""
        captured_prompt = {}

        def capture_call(prompt, **kwargs):
            captured_prompt["prompt"] = prompt
            return "Your cycle length of 48 days indicates oligomenorrhea."

        mock_gemini.side_effect = capture_call

        user, auth_header = self._create_user("Personalized User", "personalized_ai@example.com")

        from app.models.menstrual_cycle import MenstrualCycle
        from app.models.lab_report import LabReport
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=date.today() - timedelta(days=60),
            cycle_length=48,
            notes="Delayed cycle 48d",
        ))
        self.db.add(MenstrualCycle(
            user_id=user.id,
            period_start_date=date.today() - timedelta(days=12),
            cycle_length=48,
            notes="Delayed cycle 48d again",
        ))
        self.db.add(LabReport(
            user_id=user.id,
            report_name="Metabolic Labs",
            test_name="Fasting Insulin",
            test_value=24.5,
            unit="uIU/mL",
            reference_range="2.0 - 19.6",
            report_date=date.today() - timedelta(days=10),
        ))
        self.db.commit()

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "Can you interpret my cycle length and insulin?"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)

        self.assertIn("prompt", captured_prompt)
        prompt_text = captured_prompt["prompt"]
        self.assertIn("48", prompt_text)
        self.assertIn("Fasting Insulin", prompt_text)
        self.assertIn("24.5", prompt_text)

    # ==========================================================================
    # 7. Cross-User Data Isolation in AI Calls
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine._call_gemini_api")
    def test_cross_user_data_isolation_in_ai(self, mock_gemini):
        """Verify User A's AI prompt never contains User B's health records."""
        prompts_received = []

        def capture_call(prompt, **kwargs):
            prompts_received.append(prompt)
            return "Analyzed user records."

        mock_gemini.side_effect = capture_call

        user_a, auth_a = self._create_user("User Alpha", "ai_alpha@example.com")
        user_b, auth_b = self._create_user("User Beta", "ai_beta@example.com")

        from app.models.health_profile import HealthProfile
        self.db.add(HealthProfile(user_id=user_a.id, age=24, height=162, weight=56, existing_conditions=["AlphaConditionTag777"]))
        self.db.add(HealthProfile(user_id=user_b.id, age=32, height=170, weight=80, existing_conditions=["BetaConditionTag888"]))
        self.db.commit()

        # Query as User A
        res_a = self.client.post("/api/ai/chat", json={"message": "Analyze my data"}, headers=auth_a)
        self.assertEqual(res_a.status_code, 200)
        prompt_a = prompts_received[-1]

        self.assertIn("AlphaConditionTag777", prompt_a)
        self.assertNotIn("BetaConditionTag888", prompt_a)

        # Query as User B
        res_b = self.client.post("/api/ai/chat", json={"message": "Analyze my data"}, headers=auth_b)
        self.assertEqual(res_b.status_code, 200)
        prompt_b = prompts_received[-1]

        self.assertIn("BetaConditionTag888", prompt_b)
        self.assertNotIn("AlphaConditionTag777", prompt_b)

    # ==========================================================================
    # 8. Medical Safety & Emergency Escalation
    # ==========================================================================
    def test_medical_safety_and_emergency_escalation(self):
        """Verify acute clinical red flags trigger immediate emergency escalation."""
        user, auth_header = self._create_user("Emergency Patient", "emergency_ai@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "I have sudden severe acute lower pelvic pain with dizziness and fainting. What should I do?"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(body["status"], "emergency_escalation")
        self.assertTrue(body["red_flags_detected"])
        self.assertEqual(body["urgency_level"], "URGENT_EVALUATION_RECOMMENDED")
        self.assertIsNotNone(body["emergency_escalation_message"])
        self.assertIn("URGENT MEDICAL NOTICE", body["response_text"])

    # ==========================================================================
    # 9. Malformed AI Responses
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "test-gemini-key")
    @patch.object(settings, "GROQ_API_KEY", "")
    @patch.object(settings, "AI_MAX_RETRIES", 1)
    @patch("app.services.ai_engine.httpx.Client")
    def test_malformed_ai_responses_handling(self, mock_client_cls):
        """Verify engine gracefully handles empty or malformed LLM responses."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"candidates": []}
        mock_resp.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_client_cls.return_value.__enter__.return_value = mock_client

        user, auth_header = self._create_user("Malformed User", "malformed_ai@example.com")

        res = self.client.post(
            "/api/ai/chat",
            json={"message": "Explain my PCOS symptoms"},
            headers=auth_header,
        )
        self.assertEqual(res.status_code, 200)
        body = res.json()

        self.assertEqual(body["status"], "partial_deterministic")
        self.assertEqual(body["provider_used"], "deterministic_fallback")

    # ==========================================================================
    # 10. Complete Provider Failure
    # ==========================================================================
    @patch.object(settings, "GEMINI_API_KEY", "")
    @patch.object(settings, "GROQ_API_KEY", "")
    def test_complete_provider_failure_across_all_endpoints(self):
        """Verify /chat, /insights, and /copilot all succeed via deterministic fallback when no LLM is configured."""
        user, auth_header = self._create_user("Fallback User", "all_endpoints_fallback@example.com")

        # 1. /api/ai/chat
        res_chat = self.client.post(
            "/api/ai/chat",
            json={"message": "General PCOS question"},
            headers=auth_header,
        )
        self.assertEqual(res_chat.status_code, 200)
        self.assertEqual(res_chat.json()["provider_used"], "deterministic_fallback")

        # 2. /api/ai/insights
        res_insights = self.client.post(
            "/api/ai/insights",
            json={"timeframe_days": 30},
            headers=auth_header,
        )
        self.assertEqual(res_insights.status_code, 200)
        self.assertEqual(res_insights.json()["provider_used"], "deterministic_fallback")

        # 3. /api/ai/copilot
        res_copilot = self.client.post(
            "/api/ai/copilot",
            json={"action": "daily_briefing"},
            headers=auth_header,
        )
        self.assertEqual(res_copilot.status_code, 200)
        self.assertEqual(res_copilot.json()["provider_used"], "deterministic_fallback")

    # ==========================================================================
    # 11. Live API Smoke Test (Conditional)
    # ==========================================================================
    def test_live_gemini_smoke_test_conditional(self):
        """Live smoke test executed only if a genuine GEMINI_API_KEY is configured."""
        live_key = os.environ.get("GEMINI_API_KEY")
        if not live_key or not live_key.strip():
            self.skipTest("Live GEMINI_API_KEY is not set in environment. Skipping live smoke test.")

        from app.services.ai_engine import _call_gemini_api
        response_text = _call_gemini_api(
            prompt="What are the three pillars of the Rotterdam 2004 PCOS consensus criteria? Be brief.",
            system_instruction="You are a clinical decision-support engine. State medical criteria accurately.",
            api_key=live_key.strip(),
            model="gemini-2.5-flash",
            timeout_seconds=15.0,
        )
        self.assertIsNotNone(response_text)
        self.assertIn("Rotterdam", response_text)


if __name__ == "__main__":
    unittest.main()
