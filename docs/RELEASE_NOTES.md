# PCOS360 — Release Notes (v1.0.0-production)

**Release Date**: November 14, 2026  
**Build Status**: **STABLE / PRODUCTION READY**  
**Git Branch**: `main`  

---

## 1. Summary of Changes

This release delivers the complete, production-ready PCOS360 platform, encompassing the deterministic clinical calculator suite, the centralized user context engine, the multi-provider AI reasoning engine (Google Gemini & Groq), the PCOSCOPE pattern discovery dashboard, and full mobile client release builds.

---

## 2. Key Features & Capabilities

- **Deterministic Clinical Calculators**:
  - Monash 2023 international PCOS guideline menstrual cycle rhythm categorization.
  - Rotterdam consensus educational decision-support with missing-data alerts.
  - Pearson correlation engine with strict $N \ge 7$ sample size guard.
  - Configurable biomarker evaluation against standard and laboratory-provided reference intervals.
  - Emergency clinical red-flag pre-screening for acute symptoms.
- **PCOSCOPE Pattern Discovery**:
  - Interactive rolling 7-day, 30-day, and 90-day symptom and lifestyle trajectory analysis.
  - Biomarker chronological progression tracking.
  - Data completeness scoring (0–100%) and evidence-based care gap identification.
- **Centralized User Context Engine**:
  - Assembles authentic patient data from PostgreSQL with provenance and freshness tracking.
  - Enforces strict cross-user data isolation.
- **Centralized AI Intelligence Engine**:
  - Primary provider: Google Gemini Flash-Lite API.
  - Secondary provider: Groq Llama-3.3-70b API.
  - Tertiary fallback: Deterministic rule-based clinical response generator.
  - Prompt-ready clinical markdown synthesis.
- **Consultation Copilot**:
  - Structured physician appointment packet generator with personalized clinical discussion points.
- **Stateful JWT Session Management**:
  - HMAC-SHA256 tokens paired with server-side `user_sessions` tracking in PostgreSQL.
  - Instant server-side revocation on logout.

---

## 3. Verified Build Artifacts

| Component | Target Artifact | Location | Size / Status |
| :--- | :--- | :--- | :--- |
| **Android APK** | Signed Release APK | `mobile/android/app/build/outputs/apk/release/app-release.apk` | **84,492,315 bytes (~80.6 MB)** |
| **Web Frontend** | Vite Production Bundle | `frontend/dist/` | **Built in 1.25s** |
| **FastAPI Backend** | ASGI Application | `backend/` | **Production Ready** |

---

## 4. Production Deployment URLs

- **Backend API**: `https://pcos360-backend.onrender.com`
- **Backend Health Check**: `https://pcos360-backend.onrender.com/api/health`
- **Interactive API Documentation**: `https://pcos360-backend.onrender.com/docs`
- **Database**: Supabase PostgreSQL 17 (AWS Tokyo pooler)

---

## 5. Security & Clinical Disclaimers

- Zero patient records or fake biomarker values are fabricated for authenticated users.
- API keys, database credentials, and session secrets are strictly excluded from source control and logs.
- PCOS360 is an educational decision-support platform; it does not replace professional medical diagnosis, advice, or treatment.

