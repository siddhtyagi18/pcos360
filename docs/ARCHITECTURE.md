# PCOS360 — System Architecture

## 1. System Overview

PCOS360 is an end-to-end clinical intelligence and chronic condition management platform designed for polycystic ovary syndrome (PCOS). The system pairs deterministic clinical calculators, statistical pattern discovery (PCOSCOPE), and large language model (LLM) reasoning grounded strictly in authentic authenticated patient health records.

```
+-----------------------------------------------------------------------------------------+
|                                     CLIENT LAYER                                        |
|                                                                                         |
|   +------------------------------------+       +------------------------------------+   |
|   |         React 19 Web App           |       |      React Native Mobile App       |   |
|   |   (Vite, Tailwind CSS, Recharts)   |       |   (Expo 55, Hermes, Android APK)   |   |
|   +-----------------+------------------+       +-----------------+------------------+   |
+---------------------|--------------------------------------------|----------------------+
                      | (HTTPS / JSON REST API / Bearer JWT)       |
                      v                                            v
+-----------------------------------------------------------------------------------------+
|                                   FASTAPI GATEWAY                                       |
|                                                                                         |
|   - CORS Middleware (Origin Whitelisting)                                               |
|   - Rate Limiting Middleware (Sliding Window: IP & Account Throttling)                  |
|   - Auth & Session Dependency Injection (HMAC-SHA256 JWT + Server-Side Session DB)     |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
|                                    SERVICE LAYER                                        |
|                                                                                         |
|   +--------------------------+  +--------------------------+  +---------------------+   |
|   |   Clinical Calculator    |  |     PCOSCOPE Engine      |  |   Context Builder   |   |
|   | (Deterministic Monash/   |  | (Rolling 7/30/90d Rhythms|  | (Strict Isolated |   |
|   |  Rotterdam / Pearson)    |  |  Correlations N>=7, Gaps)|  |  PostgreSQL Patient |   |
|   +--------------------------+  +--------------------------+  |  Context Assembly)  |   |
|                                                               +----------+----------+   |
|                                                                          |              |
|                                 +----------------------------------------+              |
|                                 v                                                       |
|   +---------------------------------------------------------------------------------+   |
|   |                                AI Intelligence Engine                           |   |
|   |   - Primary: Google Gemini Flash-Lite (Streaming / Context Grounded)            |   |
|   |   - Secondary: Groq Llama-3.3-70b (Automated Zero-Downtime Failover)            |   |
|   |   - Tertiary: Deterministic Clinical Fallback (Safe Rule-Based Output)          |   |
|   |   - Guardrails: Pre-LLM Emergency Red-Flag Screening (Acute Pain/Hemorrhage)   |   |
|   +---------------------------------------------------------------------------------+   |
+-----------------------------------------------------------------------------------------+
                                           |
                                           v
+-----------------------------------------------------------------------------------------+
|                                    DATA PERSISTENCE                                     |
|                                                                                         |
|   Supabase Managed PostgreSQL 17 (AWS Tokyo Pooler, SSL Encrypted)                      |
|   - Users & Active User Sessions (Cryptographic JTI tracking, Instant Revocation)       |
|   - Health Profiles, Menstrual Cycles, Daily Symptoms, Lifestyle Logs                  |
|   - Laboratory Biomarkers & Clinical Documents (Cascade Deletions, User Scoping)        |
+-----------------------------------------------------------------------------------------+
```

---

## 2. Core Subsystems

### 2.1 API & Authentication Subsystem
- **Framework**: FastAPI (ASGI) with Pydantic v2 schemas.
- **Token Format**: HMAC-SHA256 JWT tokens containing `sub` (User ID) and unique `jti` (UUID).
- **Session Verification**: Every protected route executes `get_current_session`, verifying both signature validity and the presence of an unrevoked entry in `user_sessions`.
- **Database Driver Handling**: Auto-detects available database drivers (`psycopg2-binary` or `psycopg3`) across diverse host environments.

### 2.2 Deterministic Clinical Calculator (`clinical_calculator.py`)
- **Cycle Rhythm Analysis**: Classifies regularity using Monash 2023 international guideline criteria (Regular, Oligomenorrhea, Polymenorrhea, High Variance Irregularity, Amenorrhea flag >= 90 days).
- **Rotterdam Decision-Support**: Evaluates Rotterdam 2004 consensus diagnostic pillars (Ovulatory Dysfunction, Hyperandrogenism, Polycystic Morphology). Does not diagnose; clearly surfaces missing diagnostic records (e.g. absent ultrasound or androgen labs).
- **Pearson Correlation Engine**: Computes pairwise correlation coefficients ($r$) between lifestyle parameters (sleep, stress, water, exercise) and symptom intensities.
- **Minimum Data Quality Threshold**: Enforces $N \ge 7$ paired data points before reporting correlation values; prevents statistical hallucinations on small sample sizes.
- **Biomarker Reference Evaluator**: Compares raw laboratory test results against standard clinical reference intervals with support for custom lab-specific ranges.

### 2.3 PCOSCOPE Pattern Discovery Engine (`pcoscope_engine.py`)
- Analyzes longitudinal patient trends across rolling 7-day, 30-day, and 90-day observation windows.
- Clusters co-occurring symptoms by prevalence and severity progression.
- Traverses historical laboratory reports to plot biomarker trajectories over time.
- Calculates data completeness scores (0–100%) and highlights clinical care gaps (e.g. overdue lipid profile, missing OGTT).

### 2.4 User Context Engine (`context_builder.py`)
- Centralized data retrieval service.
- Aggregates health profile, cycle history, daily symptoms, lifestyle logs, lab reports, and clinical records.
- Computes provenance, timestamps, and missing-data flags.
- Formats structured clinical summaries and prompt-ready Markdown representations for LLM grounding.

### 2.5 AI Intelligence Engine (`ai_engine.py`)
- Orchestrates multi-provider AI requests.
- **Pre-screening**: Scans prompt and symptoms for acute emergency keywords (severe pain, heavy hemorrhage, fainting). Returns immediate medical referral if flags are tripped.
- **Grounding**: Injects authentic patient context assembled by `context_builder.py`.
- **Provider Fallback**:
  1. Primary: Google Gemini Flash-Lite.
  2. Secondary: Groq Llama-3.3-70b.
  3. Tertiary: Deterministic rule-based clinical response.

---

## 3. Data Flow & Security Boundary

1. Client issues request with `Authorization: Bearer <JWT>`.
2. Gateway verifies token signature and server-side session status in PostgreSQL.
3. Services query PostgreSQL filtering strictly by `user_id == current_user.id`.
4. Client-supplied `user_id` fields are ignored; data ownership is established exclusively by authenticated token claims.
5. All outbound AI prompts are assembled in server memory; API keys are never transmitted to the client.

