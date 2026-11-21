# PCOS360 – AI-Powered PCOS Health Intelligence Platform

<p align="center">
  <img src="https://img.shields.io/badge/PCOS360-Health%20Intelligence-7950A8?style=for-the-badge&logo=shield&logoColor=white" alt="PCOS360 Brand" />
</p>

<p align="center">
  <strong>Beyond Symptoms. Understand Your PCOS with Evidence-Grounded AI Intelligence.</strong>
</p>

<p align="center">
  <a href="https://github.com/siddhtyagi18/pcos360/actions"><img src="https://img.shields.io/badge/Build-Passing-10B981?style=flat-square&logo=github-actions&logoColor=white" alt="Build Status" /></a>
  <a href="https://fastapi.tiangolo.com/"><img src="https://img.shields.io/badge/FastAPI-0.115+-009688?style=flat-square&logo=fastapi&logoColor=white" alt="FastAPI" /></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-19.0-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React 19" /></a>
  <a href="https://reactnative.dev/"><img src="https://img.shields.io/badge/React%20Native-0.83-61DAFB?style=flat-square&logo=react&logoColor=black" alt="React Native" /></a>
  <a href="https://expo.dev/"><img src="https://img.shields.io/badge/Expo%20SDK-55-000020?style=flat-square&logo=expo&logoColor=white" alt="Expo SDK 55" /></a>
  <a href="https://www.postgresql.org/"><img src="https://img.shields.io/badge/PostgreSQL-17%20(Supabase)-336791?style=flat-square&logo=postgresql&logoColor=white" alt="PostgreSQL 17" /></a>
  <a href="https://ai.google.dev/"><img src="https://img.shields.io/badge/AI-Google%20Gemini%202.5%20Flash-4285F4?style=flat-square&logo=google&logoColor=white" alt="Google Gemini" /></a>
  <a href="https://groq.com/"><img src="https://img.shields.io/badge/AI%20Failover-Groq%20Llama%203.3--70b-F55036?style=flat-square" alt="Groq Failover" /></a>
  <a href="https://www.monash.edu/medicine/mchri/pcos/guideline"><img src="https://img.shields.io/badge/Guidelines-Monash%202023%20%26%20Rotterdam-8B5CF6?style=flat-square" alt="Monash 2023 Guidelines" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square" alt="License: MIT" /></a>
</p>

---

## 📑 Table of Contents

- [Overview & The Problem](#-overview--the-problem)
- [Live Showcase & Mobile Experience](#-live-showcase--mobile-experience)
- [Key Innovations & Features](#-key-innovations--features)
- [Clinical & Evidence-Based Foundation](#-clinical--evidence-based-foundation)
- [System Architecture](#-system-architecture)
- [Multi-Tier AI Intelligence Engine](#-multi-tier-ai-intelligence-engine)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Quick Start Guide](#-quick-start-guide)
- [Testing & Quality Assurance](#-testing--quality-assurance)
- [API Reference Overview](#-api-reference-overview)
- [Security, Privacy & Ethics](#-security-privacy--ethics)
- [Documentation Index](#-documentation-index)
- [Clinical Disclaimer & License](#-clinical-disclaimer--license)

---

## 💡 Overview & The Problem

**Polycystic Ovary Syndrome (PCOS)** affects **1 in 8 women worldwide** (~13% of women of reproductive age), serving as the leading global driver of ovulatory subfertility, metabolic dysregulation, and type 2 diabetes risk. Despite its staggering prevalence, **over 70% of women remain undiagnosed**, often enduring years of fragmented healthcare, invalidating consultations, and generic period-tracking apps.

### Why Traditional Apps Fail:
1. **Isolated Calendar Counting:** Standard menstrual trackers treat the cycle as an isolated calendar event, ignoring vital metabolic indicators (fasting glucose, HbA1c, insulin resistance) and hormonal signals (androgen markers, LH/FSH balance).
2. **Ungrounded "Hallucinating" Chatbots:** Generic AI assistants offer superficial, one-size-fits-all advice that is disconnected from the patient's actual electronic health records and diagnostic phenotype.
3. **Misleading Ovulation Assumptions:** Many apps declare "ovulation confirmed" based solely on calendar math, misleading patients who experience anovulatory cycles common in PCOS.

### The PCOS360 Solution:
**PCOS360** bridges patient daily self-monitoring with evidence-grounded clinical decision support. The platform integrates:
- **Deterministic Medical Calculators** rooted strictly in the **2023 Monash International PCOS Guidelines** and **Rotterdam Diagnostic Consensus**.
- **PCOSCOPE Pattern Discovery Engine** that identifies multi-week lifestyle-symptom rhythms, correlations ($N \ge 7$), and clinical care gaps.
- **Centralized User Context Engine** guaranteeing that generative AI reasoning is 100% grounded in authentic, cryptographically isolated patient data.
- **Consultation Copilot** translating daily tracking and laboratory biomarkers into a structured, 1-page physician appointment packet exported directly as a native PDF.

---

## 📱 Live Showcase & Mobile Experience

The PCOS360 mobile client is a production-compiled React Native / Expo application running the high-performance **Hermes Bytecode Engine**. The screenshots below were captured directly on physical hardware (**Xiaomi Redmi Note 10 Pro, Android 13**) running against the live Supabase PostgreSQL database and Google Gemini AI service:

### 🔬 PCOSCOPE Health Intelligence & Analytics

| 1. PCOSCOPE Live Overview | 2. Pearson Correlation Matrix ($N \ge 7$) | 3. Symptom Trends & Care Gaps |
| :---: | :---: | :---: |
| <img src="docs/assets/mobile_screen_pcoscope_live.png" width="260" alt="PCOSCOPE Overview" /> | <img src="docs/assets/mobile_screen_correlations.png" width="260" alt="Correlations Tab" /> | <img src="docs/assets/mobile_screen_trends.png" width="260" alt="Trends & Care Gaps" /> |
| *Maturity Score (100%), Monash Cycle Classification, Estimated Luteal Phase & Gemini Narrative* | *Strict $N \ge 7$ data quality threshold: Sleep vs. Fatigue ($r = -1.00$), Activity vs. Bloating ($r = -0.88$)* | *Ranked symptom clusters (Prevalence & Severity) and Monash 2023 Cardiovascular Lipid Care Gaps* |

### 🤖 Grounded AI Assistant & Doctor Consultation Copilot

| 4. Context-Grounded AI Chat | 5. Consultation Copilot | 6. Native PDF Export & Sharing |
| :---: | :---: | :---: |
| <img src="docs/assets/mobile_screen_ai_assistant.png" width="260" alt="AI Chat" /> | <img src="docs/assets/mobile_screen_copilot.png" width="260" alt="Copilot Screen" /> | <img src="docs/assets/mobile_screen_pdf_share.png" width="260" alt="PDF Share Dialog" /> |
| *Real-time clinical intelligence explaining GLUT4 glucose uptake and inositol grounding* | *Physician visit prep checklist and 4 evidence-based doctor discussion questions* | *Instant HTML-to-PDF rendering via Expo Print invoked via Android native system Share sheet* |

---

## 🌟 Key Innovations & Features

### 1. 🔭 PCOSCOPE Pattern Discovery Engine
- **Longitudinal Rhythm Tracking:** Automatically computes rolling 7-day, 30-day, and 90-day trajectory curves across cycles, daily symptoms, and lifestyle logs.
- **Statistical Correlation Matrix:** Pairwise Pearson correlation ($r$) between sleep duration, stress levels, water intake, physical activity, and symptom severity (fatigue, acne, bloating, pelvic pain).
- **Strict Data Quality Guardrail ($N \ge 7$):** Suppresses correlation reporting unless at least 7 valid paired observations exist, preventing misleading conclusions from sparse tracking.
- **Data Completeness Scoring:** Evaluates record maturity across 4 clinical pillars (Menstrual, Symptoms, Lifestyle, Biomarkers).
- **Evidence-Based Care Gap Screening:** Compares patient history against Monash 2023 guidelines to proactively identify missing tests (e.g., overdue 2-hour Oral Glucose Tolerance Test or Fasting Lipid Profile).

### 2. 🤖 Context-Grounded AI Reasoning Engine
- **Zero Hallucination Grounding:** Injects the patient's verified health records (Rotterdam phenotype, current cycle day, 30-day symptom frequency, out-of-range lab markers) into every AI prompt.
- **Pre-LLM Emergency Screening:** Immediate deterministic regex scan for acute medical emergencies (e.g., severe localized pelvic pain, heavy hemorrhage, syncope), providing emergency referral advice before invoking LLM APIs.
- **Multi-Provider Resilience:**
  - **Primary:** Google Gemini 2.5 Flash API (low-latency, medically context-grounded reasoning).
  - **Secondary:** Groq Llama-3.3-70b Versatile API (sub-second failover on rate limit or provider timeout).
  - **Tertiary:** Deterministic clinical rule fallback (zero-downtime safety net).

### 3. 🩺 Doctor Consultation Copilot
- **Structured Visit Brief:** Translates weeks of tracking data into a 1-page clinical summary tailored for gynecologists and endocrinologists.
- **Evidence-Based Discussion Questions:** Formulates targeted, guideline-backed questions based on patient-specific lab values (e.g., *"My HbA1c is 5.8%. Should we conduct a fasting insulin or OGTT?"*).
- **Native PDF Generation & Sharing:** Leverages `expo-print` and `expo-sharing` to generate and distribute high-resolution PDFs directly from the smartphone to messaging, email, or wireless printers.

### 4. 🩸 Rotterdam Phenotyping & Laboratory Biomarker Validator
- **Rotterdam Decision Support:** Evaluates the 3 classic Rotterdam consensus diagnostic criteria:
  - Pillar 1: Ovulatory dysfunction (oligo/amenorrhea).
  - Pillar 2: Clinical or biochemical hyperandrogenism.
  - Pillar 3: Polycystic ovarian morphology (ultrasound).
- **Phenotypic Categorization:** Classifies profiles into Phenotypes A (Full), B (Non-PCO morphology), C (Ovulatory), or D (Non-hyperandrogenic).
- **Biomarker Reference Range Evaluator:** Validates fasting blood glucose, HbA1c, total testosterone, free testosterone, LH/FSH ratio, and lipid panels against age-adjusted reference intervals.

### 5. 🔮 Interactive What-If Simulator
- Counterfactual modeling allowing patients to simulate the downstream impact of targeted lifestyle interventions (e.g., increasing sleep from 6.0h to 7.5h or adding 30 mins of daily resistance training) on projected fatigue and insulin sensitivity.

---

## 🏛️ Clinical & Evidence-Based Foundation

PCOS360 is built upon international medical guidelines:

| Clinical Pillar | Medical Guideline / Consensus | Implementation in PCOS360 |
| :--- | :--- | :--- |
| **Diagnostic Framework** | **Rotterdam ESHRE/ASRM Consensus (2004)** | Diagnostic criteria calculator; transparent missing criteria alerts; Phenotypes A–D. |
| **Menstrual Cycle Rhythms** | **Monash International PCOS Guideline (2023)** | Cycle irregularity thresholds: Normal (21–35 days), Oligomenorrhea (36–90 days), Amenorrhea (>90 days), High Variance (>7 days). |
| **Ovulation Safety** | **ACOG & Monash 2023 Recommendations** | **Mandatory Calendar Disclaimer:** Calendar predictions are marked as unconfirmed estimations; confirmed ovulation requires mid-luteal serum progesterone, LH surge testing, or serial ultrasound tracking. |
| **Metabolic Screening** | **Endocrine Society Clinical Practice Guidelines** | Care gap screening for 2-hour 75g OGTT, fasting insulin resistance evaluation, and annual fasting lipid profiling. |
| **Statistical Validity** | **Clinical Biostatistics Standards** | Minimum sample size threshold ($N \ge 7$) enforced before reporting Pearson correlation coefficients. |

---

## 🏗️ System Architecture

PCOS360 is architected as a decoupled, multi-tiered cloud platform prioritizing data isolation, HIPAA/GDPR architectural principles, and sub-second API responsiveness:

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
|   - CORS Middleware (Origin Whitelisting & Credential Isolation)                        |
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
|   |   - Primary: Google Gemini 2.5 Flash (Context Grounded Reasoning)               |   |
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

## ⚡ Multi-Tier AI Intelligence Engine

To guarantee 100% uptime, zero hallucinations, and safety, PCOS360 implements a 3-tier cascade:

```mermaid
flowchart TD
    UserQuery[User Health Query / Consultation Request] --> RedFlagCheck{Pre-LLM Regex Check\nAcute Pain or Hemorrhage?}
    
    RedFlagCheck -- YES --> EmergencyBanner[Return Immediate Emergency Medical Alert\nBypass LLM Processing]
    RedFlagCheck -- NO --> ContextBuilder[User Context Engine\nRetrieve Verified PostgreSQL Records]
    
    ContextBuilder --> PromptAsm[Assemble Medically Grounded Prompt\nWith Rotterdam Profile & Lab Markers]
    PromptAsm --> GeminiCall[Primary Provider: Google Gemini 2.5 Flash]
    
    GeminiCall -- Success (< 4s) --> ValidateResp[Sanitize & Format Response\nAppend Medical Disclaimer]
    GeminiCall -- Timeout / 429 / Error --> GroqFailover[Secondary Provider: Groq Llama-3.3-70b]
    
    GroqFailover -- Success (< 2s) --> ValidateResp
    GroqFailover -- Error / Unavailable --> RuleFallback[Tertiary Provider: Deterministic Clinical Fallback]
    RuleFallback --> ValidateResp
    
    ValidateResp --> Deliver[Deliver Context-Aware Health Guidance to User]
```

---

## 💻 Technology Stack

| Layer | Technology | Version | Purpose |
| :--- | :--- | :--- | :--- |
| **Backend Framework** | **FastAPI** | `0.115.6` | High-performance ASGI REST API gateway |
| **Runtime & Language**| **Python** | `3.12.8` | Backend application execution |
| **ORM & Database Driver** | **SQLAlchemy 2.0 / psycopg2** | `2.0.36` | Schema mapping and database pool connection |
| **Database** | **PostgreSQL 17 (Supabase)**| `17.2` | Managed cloud persistence on AWS Tokyo |
| **Authentication** | **PyJWT + Passlib (bcrypt)**| `2.10.1` | HMAC-SHA256 tokens and salted password hashing |
| **Primary AI Provider** | **Google Gemini API** | `gemini-2.5-flash` | High-speed, context-grounded reasoning |
| **Fallback AI Provider**| **Groq Cloud API** | `llama-3.3-70b` | Zero-latency automated failover engine |
| **Web Frontend** | **React 19 + Vite** | `19.0.0 / 8.0` | Reactive web SPA with HMR development |
| **Styling & Charts** | **Tailwind CSS + Recharts**| `3.4 / 2.15` | Responsive design and medical data visualization |
| **Mobile Framework** | **React Native + Expo SDK** | `0.83.2 / 55.0`| Universal mobile platform with native bridges |
| **Mobile Engine** | **Hermes Bytecode Engine** | `0.83` | Optimized AOT bytecode execution on Android |
| **PDF & Sharing** | **expo-print & expo-sharing** | `58.0.x` | Native HTML-to-PDF rendering and OS sharing |
| **Cloud Hosting** | **Render Web Service** | Production | Automated continuous deployment |

---

## 📂 Project Structure

```text
pcos360/
├── backend/                         # FastAPI Application Core
│   ├── app/
│   │   ├── api/routes/              # REST Endpoints (Auth, Profile, Symptoms, PCOSCOPE, AI)
│   │   ├── core/                    # Config, Database Session, Security Middleware
│   │   ├── models/                  # SQLAlchemy ORM Models (User, Cycle, Symptom, Lab)
│   │   ├── schemas/                 # Pydantic v2 Request/Response Validation Schemas
│   │   └── services/                # Clinical Calculators, Context Builder, AI Engine, PCOSCOPE
│   ├── tests/                       # Automated Test Suites (Calculators, Context, E2E)
│   ├── requirements.txt             # Python Package Dependencies
│   └── run_phase5_benchmarks.py     # Latency and Concurrency Benchmarks
│
├── frontend/                        # React 19 Web Single Page Application
│   ├── src/
│   │   ├── components/              # Navigation, Headers, Health Cards, Visual Skeletons
│   │   ├── context/                 # HealthContext & Auth State Management
│   │   ├── pages/                   # Overview, PCOSCOPE, Copilot, Labs, Tracker, What-If
│   │   └── services/api.js          # Authenticated JWT Client Service
│   ├── package.json
│   └── vite.config.js
│
├── mobile/                          # React Native / Expo Native Android App
│   ├── src/
│   │   ├── components/              # Native Mobile Cards, Grids, Modals
│   │   ├── context/                 # Mobile Session Persistence (AsyncStorage)
│   │   ├── navigation/              # Bottom Tabs & Native Stack Navigators
│   │   ├── screens/                 # Mobile Screens (Dashboard, PCOSCOPE, Copilot, Chat)
│   │   └── services/api.js          # Mobile API Bridge with Localhost / Cloud Fallback
│   ├── android/                     # Native Android Studio Project
│   │   └── app/build/outputs/apk/   # Standalone Android Release APK (84.5 MB)
│   ├── app.json                     # Expo Application Configuration
│   └── package.json
│
├── docs/                            # Comprehensive Project Documentation
│   ├── assets/                      # High-Resolution Physical Device Screenshots
│   ├── ARCHITECTURE.md              # Deep Architectural Technical Specification
│   ├── API_DOCUMENTATION.md         # Full REST API Request & Response Reference
│   ├── DATABASE_SCHEMA.md           # ERD & PostgreSQL Table Definitions
│   ├── TESTING_REPORT.md            # Automated Testing & Regression Results
│   ├── PHASE7_RELEASE_REPORT.md     # Real-Device Physical QA Certification
│   └── DEMO_SCRIPT.md               # 3-5 Minute Pitch & Walkthrough Script
│
└── README.md                        # Master Project Documentation
```

---

## 🚀 Quick Start Guide

### Prerequisites
- **Python:** `3.11` or `3.12`
- **Node.js:** `v20.x` or `v22.x` (with npm)
- **Git**
- **Android Device or Emulator** (Optional, for mobile testing)

---

### 1. Clone the Repository
```bash
git clone https://github.com/siddhtyagi18/pcos360.git
cd pcos360
```

---

### 2. Backend Setup (FastAPI & PostgreSQL)
```bash
cd backend

# Create and activate virtual environment
python -m venv venv
# Windows:
.\venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure Environment Variables
copy .env.example .env     # Windows
cp .env.example .env       # macOS/Linux
```

Configure your `backend/.env` with your credentials:
```env
DATABASE_URL=postgresql+psycopg2://postgres:YOUR_PASSWORD@YOUR_SUPABASE_HOST:6543/postgres?sslmode=require
SECRET_KEY=your-super-secret-jwt-key-at-least-32-chars-long
GEMINI_API_KEY=your-google-gemini-api-key
GROQ_API_KEY=your-groq-api-key   # Optional fallback
```

Start the backend server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- API Base: `http://localhost:8000`
- Interactive Swagger UI: `http://localhost:8000/docs`
- Redoc UI: `http://localhost:8000/redoc`

---

### 3. Web Frontend Setup (React 19 + Vite)
In a new terminal window:
```bash
cd frontend

# Install dependencies
npm install

# Start Vite development server
npm run dev
```
Open [http://localhost:5173](http://localhost:5173) in your browser.

---

### 4. Android Mobile App Setup (Expo & React Native)
In a new terminal window:
```bash
cd mobile

# Install dependencies
npm install

# Start Expo Metro Bundler
npx expo start
```

#### Install the Pre-built Release APK Directly on Android:
Connect your Android phone via USB with USB Debugging enabled, then run:
```bash
# Enable device port reverse to reach your local FastAPI backend:
adb reverse tcp:8000 tcp:8000

# Install the standalone Release APK:
adb install -r android/app/build/outputs/apk/release/app-release.apk
```

---

## 🧪 Testing & Quality Assurance

PCOS360 includes a comprehensive test suite covering mathematical formulas, database integrity, LLM grounding, and live user flows:

```bash
cd backend
```

### 1. Run Unit & Regression Test Suite (46 Tests)
```bash
python -m pytest test_clinical_calculators.py test_user_context_engine.py test_ai_engine.py test_pcoscope_engine.py -v
```
**Results:** `45 passed, 1 skipped, 0 failures` (100% core pass rate).

### 2. Run Real End-to-End Live Integration Test (12 Journeys)
Tests actual PostgreSQL persistence, JWT session cycling, and genuine Google Gemini reasoning:
```bash
python test_phase5_real_e2e.py
```
**Results:** `All 12 Real E2E Journeys Passed`.

### 3. Run Performance & Latency Benchmarks
```bash
python run_phase5_benchmarks.py
```
- **Deterministic Calculator Latency:** `< 12 ms`
- **PostgreSQL Context Assembly:** `< 85 ms`
- **Gemini AI Streaming Response:** `< 3.2 s`
- **Server-Side Session Revocation:** `< 25 ms`

---

## 📡 API Reference Overview

The platform exposes over 25 REST endpoints secured via Bearer JWT authorization:

| Domain | Method | Endpoint | Description |
| :--- | :--- | :--- | :--- |
| **Auth** | `POST` | `/api/auth/register` | Register account & issue initial JWT token |
| **Auth** | `POST` | `/api/auth/login` | Authenticate credentials & record session in DB |
| **Auth** | `POST` | `/api/auth/logout` | Revoke current server session immediately |
| **Profile** | `GET/POST`| `/api/profile/` | Manage user health metrics (Age, Height, Weight, BMI) |
| **Cycles** | `GET/POST`| `/api/cycles/` | Log menstrual cycles and evaluate Monash regularity |
| **Symptoms**| `GET/POST`| `/api/symptoms/` | Track daily fatigue, acne, bloating, pelvic pain |
| **Lifestyle**| `GET/POST`| `/api/lifestyle/` | Log sleep hours, stress scores, water, and exercise |
| **Labs** | `GET/POST`| `/api/lab-reports/` | Ingest lab biomarkers & compare with reference intervals |
| **PCOSCOPE**| `GET` | `/api/pcoscope/analysis` | Retrieve longitudinal rhythm, correlations & care gaps |
| **PCOSCOPE**| `GET` | `/api/pcoscope/insights` | Retrieve AI-synthesized doctor discussion points |
| **AI** | `POST` | `/api/ai/chat` | Context-grounded health chat with red-flag screening |
| **AI** | `POST` | `/api/ai/copilot` | Generate doctor consultation packet summary |
| **Context** | `GET` | `/api/health-context/me`| Retrieve complete isolated patient health context |

Full request and response schemas are detailed in [`docs/API_DOCUMENTATION.md`](docs/API_DOCUMENTATION.md).

---

## 🔒 Security, Privacy & Ethics

1. **Strict Cross-User Isolation:** Every database transaction enforces `user_id == current_user.id` at the SQLAlchemy ORM layer. No tenant can view or mutate another user's records.
2. **Stateful Session Revocation:** JWTs carry unique cryptographic `jti` identifiers checked against PostgreSQL on every request. Logging out revokes the session in under 25ms, rendering stolen tokens immediately unusable.
3. **No Synthetic Fallbacks for Real Users:** If a user hasn't logged lab tests or cycles, the platform explicitly displays empty states and care gap alerts instead of fabricating dummy data.
4. **Credential Security:** API keys (`GEMINI_API_KEY`, `GROQ_API_KEY`, `SECRET_KEY`) reside exclusively in server-side `.env` files and are never bundled in web or mobile client code.
5. **Rate Limiting & Brute-Force Protection:** Sliding window IP and account rate limiting blocks automated credential stuffing and API abuse.

---

## 📚 Documentation Index

Deep dive into the project's engineering, clinical, and deployment documentation:

- 🏛️ [System Architecture Specification](docs/ARCHITECTURE.md)
- 🗄️ [Database Schema & ERD Documentation](docs/DATABASE_SCHEMA.md)
- 📡 [Complete REST API Specification](docs/API_DOCUMENTATION.md)
- 💻 [Local Developer Setup Guide](docs/SETUP_GUIDE.md)
- 🚀 [Production Cloud Deployment Guide](docs/DEPLOYMENT_GUIDE.md)
- 📱 [Android Release Build & Device QA Guide](docs/ANDROID_RELEASE_GUIDE.md)
- 📱 [Phase 7 Physical Device QA Certification](docs/PHASE7_RELEASE_REPORT.md)
- 🔒 [Security & Privacy Architecture](docs/SECURITY_PRIVACY.md)
- ⚠️ [Known Limitations & Future Scope](docs/KNOWN_LIMITATIONS.md)
- 🧪 [Automated Testing & Benchmark Report](docs/TESTING_REPORT.md)
- 🎬 [Project Demonstration Script (3-5 min)](docs/DEMO_SCRIPT.md)
- 🏷️ [Release Notes (v1.0.0-production)](docs/RELEASE_NOTES.md)

---

## ⚖️ Clinical Disclaimer & License

### Medical & Ethical Disclaimer
> **IMPORTANT:** PCOS360 is an educational health intelligence platform designed to support informed discussions between patients and licensed healthcare professionals. It does not provide medical diagnoses, treatment prescriptions, or definitive ovulation confirmations. Menstrual cycle phase calculations are calendar-based estimates; physiological confirmation requires clinical serum assays or ultrasound follicular tracking. If experiencing severe pelvic pain, heavy vaginal bleeding, or fainting, seek immediate emergency medical care.

### License
This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<p align="center">
  Built with ❤️ for Women's Health & Clinical AI Rigor.<br/>
  <strong>PCOS360</strong> • <em>Beyond Symptoms. Understand Your PCOS.</em>
</p>
