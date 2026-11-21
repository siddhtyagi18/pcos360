# PCOS360 — API Documentation

## 1. Base URL & Authentication

- **Production Cloud**: `https://pcos360-backend.onrender.com/api`
- **Local Development**: `http://localhost:8000/api`

Protected endpoints require a Bearer token in the request header:
```http
Authorization: Bearer <access_token>
```

---

## 2. Authentication Endpoints

### 2.1 Register New Account
`POST /api/auth/register`
- **Rate Limit**: 10 attempts per 300s window.
- **Request Body**:
```json
{
  "full_name": "Jane Doe",
  "email": "jane@example.com",
  "password": "StrongPassword123!"
}
```
- **Response** (`201 Created`):
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "expires_at": "2026-11-21T16:30:00Z",
  "user": {
    "id": 12,
    "full_name": "Jane Doe",
    "email": "jane@example.com",
    "is_active": true
  }
}
```

### 2.2 Sign In
`POST /api/auth/login`
- **Rate Limit**: 5 attempts per account / 20 per IP per 300s.
- **Request Body**:
```json
{
  "email": "jane@example.com",
  "password": "StrongPassword123!"
}
```
- **Response** (`200 OK`): Same as Register.

### 2.3 Sign Out (Revoke Session)
`POST /api/auth/logout`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
{
  "message": "Successfully logged out. Server session has been revoked."
}
```

---

## 3. PCOSCOPE Intelligence Endpoints

### 3.1 Pattern Discovery Analysis
`GET /api/pcoscope/analysis?window_days=30`
- **Headers**: `Authorization: Bearer <token>`
- **Query Params**: `window_days` (`7`, `30`, `90`; default: `30`).
- **Response** (`200 OK`):
```json
{
  "user_id": 12,
  "analysis_timestamp": "2026-11-14T22:00:00Z",
  "data_completeness": {
    "overall_score_pct": 85,
    "profile_initialized": true,
    "cycles_logged_count": 4,
    "symptoms_logged_days": 18,
    "lifestyle_logged_days": 18,
    "lab_biomarkers_count": 5,
    "missing_critical_elements": ["Pelvic Ultrasound"],
    "recommendation": "Track daily symptoms consistently to strengthen 30-day pattern confidence."
  },
  "cycle_patterns": {
    "sample_size": 4,
    "has_sufficient_data": true,
    "mean_length_days": 34.2,
    "rhythm_classification": "Regular Menstrual Rhythm",
    "is_irregular": false,
    "estimated_current_phase": "Follicular Phase (Day 9)",
    "ovulation_confirmation_status": "UNCONFIRMED: Calendar estimation only. True clinical confirmation requires mid-luteal serum progesterone (>= 3 ng/mL) or serial ultrasound."
  },
  "lifestyle_correlations": [
    {
      "factor_a": "Sleep Duration (hours)",
      "factor_b": "Fatigue Severity (1-10)",
      "sample_size": 18,
      "correlation_coefficient": -0.82,
      "direction": "negative",
      "strength": "strong",
      "has_sufficient_data": true,
      "data_quality_warning": null,
      "clinical_interpretation": "Longer sleep duration strongly associates with lower reported fatigue."
    }
  ],
  "care_gaps": [
    {
      "gap_id": "gap_ogtt",
      "category": "Metabolic",
      "title": "Oral Glucose Tolerance Test (OGTT) Recommended",
      "guideline_source": "Monash 2023 International PCOS Guideline",
      "urgency": "medium",
      "action_summary": "Discuss baseline 2-hour 75g OGTT screening with your clinician."
    }
  ],
  "disclaimer": "Educational medical decision-support only. Does not constitute a medical diagnosis."
}
```

### 3.2 AI Insights Synthesis
`GET /api/pcoscope/insights?window_days=30`
- **Headers**: `Authorization: Bearer <token>`
- **Response** (`200 OK`):
```json
{
  "provider_used": "gemini",
  "model_used": "gemini-flash-lite-latest",
  "narrative_synthesis": "Based on your 18 days of paired check-ins...",
  "key_findings": [
    "Inverse correlation observed between sleep duration and afternoon fatigue.",
    "Cycle interval demonstrates mild variance (32-36 days)."
  ],
  "doctor_discussion_points": [
    "Review OGTT metabolic screening options.",
    "Evaluate androgen panel trends."
  ],
  "lifestyle_actions": [
    "Prioritize consistent 7.5 to 8 hours sleep schedule."
  ],
  "disclaimer": "Educational medical decision-support only."
}
```

---

## 4. AI & Copilot Endpoints

### 4.1 Personalized AI Health Chat
`POST /api/ai/chat`
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "message": "Why does my fatigue spike when I get less than 7 hours of sleep?",
  "conversation_history": []
}
```
- **Response** (`200 OK`):
```json
{
  "reply": "Looking at your tracked records, your sleep logs indicate...",
  "provider_used": "gemini",
  "model_used": "gemini-flash-lite-latest",
  "is_emergency": false,
  "data_sources_used": ["health_profile", "lifestyle_logs", "daily_symptoms"],
  "disclaimer": "PCOS360 AI is an educational assistant and cannot diagnose or prescribe."
}
```

### 4.2 Consultation Copilot Packet
`POST /api/ai/copilot`
- **Headers**: `Authorization: Bearer <token>`
- **Request Body**:
```json
{
  "specialty_focus": "Endocrinology",
  "focus_concerns": ["Fatigue", "Irregular cycles"]
}
```
- **Response** (`200 OK`): Returns an appointment packet containing clinical history summary, biomarker delta table, care gaps, and tailored questions for the doctor.

---

## 5. Health Context Endpoints

### 5.1 Full User Context
`GET /api/health-context/me`
- Returns structured JSON representation of all patient modules.

### 5.2 Markdown Clinical Summary
`GET /api/health-context/me/summary`
- Returns prompt-ready formatted Markdown string summarizing user health records.

---

## 6. System Health Endpoint

`GET /api/health`
- **Public endpoint (No auth required)**.
- **Response** (`200 OK`):
```json
{
  "status": "healthy",
  "service": "PCOS360 Backend",
  "version": "1.0.0",
  "database": {
    "status": "connected",
    "type": "PostgreSQL"
  }
}
```

