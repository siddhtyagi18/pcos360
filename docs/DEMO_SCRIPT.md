# PCOS360 — Final Project Demonstration Script (3–5 Minutes)

## Target Audience
Clinical advisors, healthcare evaluators, engineering leadership, and prospective users.

---

## 1. Opening & Problem Statement (0:00 – 0:45)

> *"Polycystic ovary syndrome (PCOS) affects 1 in 8 women globally. It is the leading cause of endocrine and ovulatory infertility. Yet, 70% of women remain undiagnosed or struggle through fragmented care. Generic health apps fail because they isolate menstrual cycles from metabolic indicators, give generic advice, or make unsupported diagnostic claims.*
>
> *Introducing **PCOS360** — an AI-powered women's health intelligence platform designed to bridge the gap between patient daily tracking and evidence-grounded clinical decision support."*

---

## 2. Architecture & Technological Rigor (0:45 – 1:30)

> *"PCOS360 is built on a four-pillar architecture:
> 1. **Client Layer**: A responsive React 19 web application and an Expo React Native mobile application for Android.
> 2. **API & Security Gateway**: FastAPI with HMAC-SHA256 JWT tokens and stateful server-side session revocation in PostgreSQL.
> 3. **Deterministic Clinical Core**: Mathematical engines implementing Monash 2023 international guidelines, Rotterdam educational consensus, and Pearson correlation matrices with strict $N \ge 7$ sample size guards.
> 4. **AI Intelligence Engine**: A multi-tiered LLM reasoning pipeline powered by Google Gemini Flash-Lite with automatic failover to Groq Llama-3.3-70b and safe deterministic clinical fallbacks."*

---

## 3. Live Platform Walkthrough (1:30 – 3:30)

### Scene 1: Authentic Onboarding & Health Profile
> *"Let's log in to Jane's account. Notice that all metrics are live and authentic — no hardcoded dummy data. Her profile records age, BMI, and confirmed PCOS diagnosis. Her session token is tracked in Supabase PostgreSQL."*

### Scene 2: PCOSCOPE Pattern Discovery
> *"Navigating to the **PCOSCOPE** tab, we see the power of our deterministic engine. In the 30-day window, Jane has logged 18 days of paired lifestyle and symptom check-ins.
> - Notice the cycle rhythm classification: calculated strictly via Monash thresholds.
> - Notice the correlation card: sleep duration vs. fatigue severity yields a correlation coefficient of $r = -0.82$. Because her sample size is $N = 18$ ($\ge 7$), the engine confirms statistical sufficiency.
> - Notice the clinical safety disclaimer: calendar-based ovulation is clearly tagged as **UNCONFIRMED**, requiring progesterone or ultrasound confirmation before asserting clinical certainty."*

### Scene 3: Grounded AI Health Assistant
> *"In the **AI Health Chat**, Jane asks: 'Why is my fatigue worse on days I sleep under 7 hours?'
> Notice the response time: ~5 seconds. The AI does not hallucinate generic advice. It retrieves Jane's actual PostgreSQL logs via the User Context Engine, highlights her sleep numbers, explains the cortisol-insulin dynamic, and includes standard clinical disclaimers."*

### Scene 4: Doctor Consultation Copilot
> *"When Jane prepares for her upcoming endocrinology visit, the **Consultation Copilot** generates a one-page clinical packet. It condenses 3 months of cycle variance, out-of-range lab markers, care gaps like an overdue OGTT, and provides four targeted questions for Jane to ask her physician."*

---

## 4. Security, Privacy & Safety Summary (3:30 – 4:15)

> *"Medical safety is paramount:
> - **Pre-LLM Emergency Screening**: Keywords like acute pelvic pain or hemorrhage immediately bypass the AI and deliver instant emergency guidance.
> - **Strict User Isolation**: All queries filter strictly by the cryptographically verified user ID.
> - **Zero Fabrication**: Missing tests are surfaced as care gaps, never invented.
> - **Instant Session Revocation**: When Jane logs out, her session is marked revoked in PostgreSQL, blocking token reuse."*

---

## 5. Conclusion & Future Roadmap (4:15 – 4:45)

> *"PCOS360 demonstrates that generative AI in women's health must be bounded by deterministic clinical calculators and verified electronic health records.
>
> In our next development cycle, we aim to introduce EHR FHIR interoperability, continuous wearable glucose sensor integration, and validated clinical pilot trials.
>
> Thank you, and we welcome your questions!"*

