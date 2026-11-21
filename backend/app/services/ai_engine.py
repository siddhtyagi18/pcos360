"""Centralized AI Intelligence Engine for PCOS360.

Orchestrates multi-provider AI reasoning grounded in authentic patient health data
and curated clinical guidelines (Monash 2023, Rotterdam 2004, Endocrine Society 2013).

PROVIDER HIERARCHY:
1. Primary: Google Gemini API (REST)
2. Secondary / Fallback: Groq API (REST)
3. Deterministic Safety Fallback: Pure rule-based clinical report when all LLMs are unreachable.

SAFETY & COMPLIANCE GUARANTEES:
- No autonomous diagnosis or medication dosage recommendations.
- Deterministic emergency red-flag screening runs prior to external API calls.
- Authentic patient health context injected from verified session tokens only.
- Transparent reporting of missing clinical data, unperformed tests, and insufficient sample sizes.
- Zero fabrication: Never invents lab numbers or predicts outcomes without authentic data.
- API keys and patient PII are never logged or exposed to client applications.
"""

from datetime import datetime, timezone
import json
import logging
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.medical_knowledge import MEDICAL_SOURCES
from app.models.user import User
from app.schemas.ai import AIChatRequest, AICopilotRequest, AIInsightsRequest, AIResponse
from app.services.clinical_calculator import screen_urgent_symptoms
from app.services.context_builder import UserHealthContext, build_user_health_context

logger = logging.getLogger("pcos360.ai_engine")

# Canonical Medical Guideline Citations
CANONICAL_CITATIONS = [
    "Monash 2023 International Evidence-Based Guideline for the Assessment and Management of Polycystic Ovary Syndrome",
    "Rotterdam ESHRE/ASRM-Sponsored PCOS Consensus Workshop Group (2004)",
    "Endocrine Society Clinical Practice Guideline for Diagnosis and Treatment of PCOS (2013)",
    "Androgen Excess and PCOS (AE-PCOS) Society Criteria (2009)",
]

# Standard Medical Safety Disclaimer
STANDARD_DISCLAIMER = (
    "Educational decision-support only. This information is not an automated medical diagnosis, "
    "prescription, or substitute for individualized clinical evaluation by a licensed healthcare professional."
)

# Master Clinical System Prompt
MASTER_SYSTEM_PROMPT = """You are the PCOS360 Clinical Intelligence Assistant, an evidence-based medical decision-support engine for Polycystic Ovary Syndrome (PCOS).

YOUR ROLE:
Provide helpful, empathetic, scientifically grounded explanations to the patient based on their actual health records and established international guidelines.

CLINICAL GUIDELINE GROUNDING:
1. Rotterdam 2004 Criteria: PCOS diagnosis requires at least 2 of 3 pillars:
   - Ovulatory dysfunction (irregular, delayed, or absent cycles)
   - Hyperandrogenism (biochemical elevated androgens or clinical signs like hirsutism/severe acne)
   - Polycystic ovarian morphology (ultrasound PCOM: >= 20 follicles per ovary or ovarian volume >= 10 ml)
   - Mandatory: Must exclude confounding mimickers (thyroid disease, hyperprolactinemia, congenital adrenal hyperplasia).
2. Monash 2023 International Guidelines:
   - Adult cycle intervals: 21 to 35 days (regular). > 35 days (oligomenorrhea). >= 90 days (secondary amenorrhea).
   - High variability: Variance > 7-10 days between cycles indicates cycle irregularity.
   - First-line intervention: Evidence-based lifestyle modification (balanced Low-GI nutrition, restorative sleep, regular physical activity).
   - First-line pharmacological options: Combined oral contraceptives and/or Metformin for metabolic features (to be prescribed only by a licensed physician).
3. Endocrine Society 2013 & AE-PCOS Society 2009 Guidelines.

CRITICAL MEDICAL SAFETY RULES:
1. DO NOT DIAGNOSE: Never say "You have PCOS" or "You have Phenotype A". Use educational alignment: "Your recorded data aligns with patterns seen in...", and emphasize that a formal diagnosis requires a physician to rule out mimickers.
2. DO NOT PRESCRIBE OR ALTER DOSAGES: Never recommend specific drug dosages or suggest starting/stopping pharmaceuticals.
3. ADHERE STRICTLY TO AUTHENTIC RECORDS:
   - Ground all personalized statements in the provided "# CLINICAL HEALTH CONTEXT".
   - If an ultrasound, lab report, or cycle length is missing or unrecorded, STATE CLEARLY that it is missing.
   - NEVER invent or assume normal/abnormal values for unperformed tests.
4. URGENT CLINICAL RED FLAGS:
   - If the user reports severe acute lower abdominal/pelvic pain, sudden fever, heavy hemorrhagic vaginal bleeding (e.g. soaking 2+ pads/hour for 2 hours), or syncope/fainting, prioritize recommending IMMEDIATE emergency medical evaluation (to rule out ovarian torsion, cyst rupture, or hemorrhage).
5. TRANSPARENT UNCERTAINTY: Clearly communicate the limits of digital tracking and statistical correlations (correlation != medical causation).
6. EMPATHY & CLARITY: Write in warm, accessible, professional language using clear markdown formatting.
"""


class AIEngineError(Exception):
    """Base exception for AI engine failures."""
    pass


# ==============================================================================
# Provider HTTP Callers
# ==============================================================================

def _call_gemini_api(
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> str:
    """Call the Google Gemini REST API using httpx."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": prompt}],
            }
        ],
        "systemInstruction": {
            "parts": [{"text": system_instruction}],
        },
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 2048,
        },
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, json=payload, headers={"Content-Type": "application/json"})
        response.raise_for_status()
        data = response.json()

    candidates = data.get("candidates", [])
    if not candidates:
        raise AIEngineError("Gemini returned an empty candidate list.")

    parts = candidates[0].get("content", {}).get("parts", [])
    if not parts or "text" not in parts[0]:
        raise AIEngineError("Gemini response missing text part.")

    return parts[0]["text"].strip()


def _call_groq_api(
    prompt: str,
    system_instruction: str,
    api_key: str,
    model: str,
    timeout_seconds: float,
) -> str:
    """Call the Groq REST API (OpenAI-compatible) using httpx."""
    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 2048,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    with httpx.Client(timeout=timeout_seconds) as client:
        response = client.post(url, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

    choices = data.get("choices", [])
    if not choices:
        raise AIEngineError("Groq returned empty choices.")

    content = choices[0].get("message", {}).get("content")
    if not content:
        raise AIEngineError("Groq response missing message content.")

    return content.strip()


# ==============================================================================
# Centralized AI Dispatcher with Retries and Fallbacks
# ==============================================================================

def _dispatch_ai_request(
    prompt: str,
    system_prompt: str = MASTER_SYSTEM_PROMPT,
) -> Tuple[str, str, str]:
    """Execute AI prompt across the provider hierarchy with controlled retries.

    Returns:
    - Tuple: (response_text, provider_name, model_name)
    Raises:
    - AIEngineError if all configured providers fail.
    """
    timeout = settings.AI_REQUEST_TIMEOUT_SECONDS
    max_retries = max(1, settings.AI_MAX_RETRIES)
    errors: List[str] = []

    # 1. Primary: Google Gemini API
    gemini_key = str(settings.GEMINI_API_KEY or "").strip()
    gemini_model = str(settings.GEMINI_MODEL or "gemini-flash-lite-latest").strip()
    gemini_models_to_try = [gemini_model]
    if "gemini-flash-lite-latest" not in gemini_models_to_try:
        gemini_models_to_try.append("gemini-flash-lite-latest")

    if gemini_key:
        for current_model in gemini_models_to_try:
            for attempt in range(max_retries):
                try:
                    t0 = time.time()
                    text = _call_gemini_api(
                        prompt=prompt,
                        system_instruction=system_prompt,
                        api_key=gemini_key,
                        model=current_model,
                        timeout_seconds=timeout,
                    )
                    elapsed = round((time.time() - t0) * 1000)
                    logger.info("Gemini generation succeeded with %s on attempt %d (%d ms)", current_model, attempt + 1, elapsed)
                    return text, "gemini", str(current_model)
                except httpx.HTTPStatusError as exc:
                    status = exc.response.status_code
                    errors.append(f"Gemini ({current_model}) HTTP {status}")
                    logger.warning("Gemini (%s) HTTP error %d: %s", current_model, status, exc)
                    # Don't retry client errors (bad auth, invalid request) on the same model
                    if 400 <= status < 500:
                        break
                except (httpx.TimeoutException, httpx.RequestError, AIEngineError) as exc:
                    errors.append(f"Gemini ({current_model}) error: {type(exc).__name__}")
                    logger.warning("Gemini (%s) attempt %d failed: %s", current_model, attempt + 1, type(exc).__name__)
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))
    else:
        errors.append("Gemini API key not configured")

    # 2. Secondary: Groq API
    groq_key = str(settings.GROQ_API_KEY or "").strip()
    groq_model = str(settings.GROQ_MODEL or "llama-3.3-70b-versatile").strip()

    if groq_key:
        for attempt in range(max_retries):
            try:
                t0 = time.time()
                text = _call_groq_api(
                    prompt=prompt,
                    system_instruction=system_prompt,
                    api_key=groq_key,
                    model=groq_model,
                    timeout_seconds=timeout,
                )
                elapsed = round((time.time() - t0) * 1000)
                logger.info("Groq fallback succeeded on attempt %d (%d ms)", attempt + 1, elapsed)
                return text, "groq", str(groq_model)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                errors.append(f"Groq HTTP {status}")
                logger.warning("Groq HTTP error %d: %s", status, exc)
                if 400 <= status < 500:
                    break
            except (httpx.TimeoutException, httpx.RequestError, AIEngineError) as exc:
                errors.append(f"Groq error: {type(exc).__name__}")
                logger.warning("Groq attempt %d failed: %s", attempt + 1, type(exc).__name__)
                if attempt < max_retries - 1:
                    time.sleep(0.5 * (attempt + 1))
    else:
        errors.append("Groq API key not configured")

    raise AIEngineError(f"All AI providers unavailable: {'; '.join(errors)}")


# ==============================================================================
# Deterministic Clinical Report Fallback
# ==============================================================================

def _generate_deterministic_clinical_fallback(
    user_query: str,
    context: Optional[UserHealthContext],
    red_flags: Dict[str, Any],
) -> str:
    """Generate an honest, pure rule-based clinical report when external LLMs are unavailable.

    Guarantees that the patient always receives their authentic deterministic calculations
    without any LLM hallucinations or silent failure.
    """
    lines = [
        "## Notice: Deterministic Clinical Mode Active",
        "External AI language processing services are temporarily unavailable or in maintenance mode. "
        "Below is your **authentic, deterministic clinical health report** calculated directly from "
        "your recorded data and established clinical guidelines (Monash 2023 & Rotterdam 2004).\n",
    ]

    if red_flags.get("has_urgent_symptoms"):
        lines.extend([
            "### ⚠️ URGENT CLINICAL ALERT",
            red_flags.get("escalation_message", "Please seek medical evaluation immediately."),
            "",
        ])

    if context:
        # Profile
        lines.append("### 1. Patient Profile")
        if context.profile.is_present:
            bmi_str = f"{context.profile.calculated_bmi} kg/m² ({context.profile.bmi_category})" if context.profile.calculated_bmi else "Not calculated"
            lines.append(f"- Age: {context.profile.age or 'Unspecified'} | BMI: {bmi_str}")
            lines.append(f"- Status: {context.profile.diagnosis_status or 'Unspecified'}")
            if context.profile.existing_conditions:
                lines.append(f"- Existing Conditions: {', '.join(context.profile.existing_conditions)}")
            if context.profile.medications:
                lines.append(f"- Active Medications: {', '.join(context.profile.medications)}")
        else:
            lines.append("- Health profile has not been initialized.")

        # Cycles
        lines.append("\n### 2. Menstrual Cycle Regularity (Monash 2023)")
        if context.cycles.is_present and context.cycles.total_recorded_cycles > 0:
            stats = context.cycles.statistics
            lines.append(f"- Recorded Cycles: {context.cycles.total_recorded_cycles}")
            lines.append(f"- Rhythm: {stats.get('rhythm_classification', 'Unclassified')}")
            lines.append(f"- Clinical Interpretation: {stats.get('clinical_interpretation', 'N/A')}")
        else:
            lines.append(f"- {context.cycles.missing_data_note or 'No cycles logged.'}")

        # Biomarkers
        lines.append("\n### 3. Laboratory Biomarkers")
        if context.labs.is_present and context.labs.evaluated_biomarkers:
            lines.append(f"- Total Biomarkers Logged: {context.labs.total_biomarkers_recorded}")
            if context.labs.abnormal_biomarkers:
                lines.append("- Out-of-Range Parameters:")
                for b in context.labs.abnormal_biomarkers:
                    lines.append(f"  * {b.get('canonical_name')}: {b.get('numeric_value')} {b.get('reported_unit') or b.get('standard_unit')} ({b.get('status')})")
            else:
                lines.append("- All recorded biomarkers fall within reference intervals.")
        else:
            lines.append(f"- {context.labs.missing_data_note or 'No laboratory biomarkers logged.'}")

        # Rotterdam
        lines.append("\n### 4. Educational Rotterdam Criteria Assessment")
        rotterdam = context.clinical.rotterdam_assessment
        if rotterdam:
            lines.append(f"- Educational Alignment: {rotterdam.get('educational_phenotype_alignment', 'Unassigned')}")
            lines.append(f"- Supported Pillars: {rotterdam.get('criteria_present_count', 0)} of 3 documented")
            missing_docs = rotterdam.get("criteria_missing_documentation", [])
            if missing_docs:
                lines.append("- Missing Diagnostic Investigations:")
                for d in missing_docs:
                    lines.append(f"  * {d}")

        # Missing summary
        if context.missing_data_summary:
            lines.append("\n### 5. Identified Clinical Data Gaps")
            for gap in context.missing_data_summary:
                lines.append(f"- {gap}")
    else:
        lines.append("No patient context was loaded for this session.")

    lines.extend([
        "\n---",
        "**Next Steps**:",
        "1. Discuss this summary with your treating physician or gynecologist.",
        "2. Continue logging your daily symptoms and sleep to discover authentic mathematical patterns.",
    ])

    return "\n".join(lines)


# ==============================================================================
# Public AI Engine Services
# ==============================================================================

def generate_chat_response(
    db: Session,
    user: User,
    request: AIChatRequest,
) -> AIResponse:
    """Generate a personalized, context-aware conversational response for the authenticated user.

    Strictly uses authentic user records, performs red-flag screening, grounds answers
    in international clinical guidelines, and supports graceful deterministic fallback.
    """
    user_query = request.message.strip()

    # 1. Screen user query for acute medical red flags
    red_flag_res = screen_urgent_symptoms(
        symptoms=[user_query],
        notes=None,
    )

    # 2. Retrieve authentic patient context if requested
    context: Optional[UserHealthContext] = None
    context_str = ""
    missing_data_noted: List[str] = []
    deterministic_insights: Optional[Dict[str, Any]] = None

    if request.include_context:
        context = build_user_health_context(db=db, user=user)
        context_str = context.to_clinical_prompt_text()
        missing_data_noted = list(context.missing_data_summary)

        # Include recent symptom red flags if detected in context
        if context.symptoms.red_flag_screening.get("has_urgent_symptoms"):
            red_flag_res = context.symptoms.red_flag_screening

        deterministic_insights = {
            "profile_bmi": context.profile.calculated_bmi,
            "cycle_rhythm": context.cycles.statistics.get("rhythm_classification"),
            "rotterdam_phenotype": context.clinical.rotterdam_assessment.get("educational_phenotype_alignment"),
            "abnormal_biomarkers_count": len(context.labs.abnormal_biomarkers),
        }

    # 3. Assemble the prompt
    history_str = ""
    if request.conversation_history:
        history_lines = []
        for msg in request.conversation_history[-4:]:  # Keep recent history
            history_lines.append(f"{msg.role.capitalize()}: {msg.content}")
        history_str = "## PRIOR CONVERSATION:\n" + "\n".join(history_lines) + "\n\n"

    focus_instruction = ""
    if request.focus_domain:
        focus_instruction = f"\nFocus area requested by user: {request.focus_domain}. Pay special attention to this domain.\n"

    full_prompt = (
        f"{context_str}\n\n"
        f"{history_str}"
        f"{focus_instruction}"
        f"## USER INQUIRY:\n{user_query}\n\n"
        f"Respond directly to the user's inquiry, incorporating their personal health records above where relevant. "
        f"If data is missing, state so transparently. Never invent mock lab results or diagnoses."
    )

    # 4. Attempt AI Generation with Fallback
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    response_text = ""
    status = "success"

    try:
        response_text, provider_used, model_used = _dispatch_ai_request(
            prompt=full_prompt,
            system_prompt=MASTER_SYSTEM_PROMPT,
        )
    except AIEngineError as exc:
        logger.warning("AI providers failed (%s). Engaging deterministic clinical fallback.", exc)
        response_text = _generate_deterministic_clinical_fallback(
            user_query=user_query,
            context=context,
            red_flags=red_flag_res,
        )
        provider_used = "deterministic_fallback"
        model_used = "clinical_rule_engine"
        status = "partial_deterministic"

    # Prepend urgent red flag warning if active
    if red_flag_res.get("has_urgent_symptoms"):
        status = "emergency_escalation"
        escalation_notice = (
            f"> [!CAUTION]\n> **URGENT MEDICAL NOTICE**: {red_flag_res.get('escalation_message')}\n\n"
        )
        response_text = escalation_notice + response_text

    return AIResponse(
        status=status,
        response_text=response_text,
        provider_used=str(provider_used) if provider_used is not None else None,
        model_used=str(model_used) if model_used is not None else None,
        is_personalized=request.include_context,
        red_flags_detected=red_flag_res.get("has_urgent_symptoms", False),
        urgency_level=red_flag_res.get("urgency_level", "ROUTINE"),
        emergency_escalation_message=red_flag_res.get("escalation_message") if red_flag_res.get("has_urgent_symptoms") else None,
        missing_data_noted=missing_data_noted,
        citations=list(CANONICAL_CITATIONS),
        deterministic_insights=deterministic_insights,
        disclaimer=STANDARD_DISCLAIMER,
    )


def generate_insights_response(
    db: Session,
    user: User,
    request: AIInsightsRequest,
) -> AIResponse:
    """Generate an analytical clinical insight report synthesising cycles, biomarkers, and lifestyle."""
    context = build_user_health_context(db=db, user=user)

    prompt = (
        f"{context.to_clinical_prompt_text()}\n\n"
        f"## TASK: COMPREHENSIVE CLINICAL HEALTH INSIGHTS (Last {request.timeframe_days} Days)\n"
        f"Synthesize the user's authentic health records into a structured analytical report:\n"
        f"1. Executive Health Summary (Demographics, diagnosis status, BMI).\n"
        f"2. Menstrual Pattern Analysis (Rhythm, regularity, variance vs Monash 2023 guidelines).\n"
        f"3. Biomarker & Metabolic Status (Laboratory findings, reference ranges, abnormal indicators).\n"
        f"4. Lifestyle & Symptom Dynamics (Statistically verified correlations if N >= 7; otherwise honest gap report).\n"
        f"5. Educational Rotterdam Alignment (Phenotype discussion, missing tests).\n"
        f"6. Actionable Discussion Points for Clinician Appointment.\n"
        f"Do not invent values. State gaps clearly."
    )

    red_flags = context.symptoms.red_flag_screening
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    response_text = ""
    status = "success"

    try:
        response_text, provider_used, model_used = _dispatch_ai_request(prompt=prompt)
    except AIEngineError as exc:
        logger.warning("AI providers failed for insights (%s). Engaging deterministic fallback.", exc)
        response_text = _generate_deterministic_clinical_fallback(
            user_query="Comprehensive Health Insights",
            context=context,
            red_flags=red_flags,
        )
        provider_used = "deterministic_fallback"
        model_used = "clinical_rule_engine"
        status = "partial_deterministic"

    if red_flags.get("has_urgent_symptoms"):
        status = "emergency_escalation"
        response_text = (
            f"> [!CAUTION]\n> **URGENT MEDICAL NOTICE**: {red_flags.get('escalation_message')}\n\n"
            + response_text
        )

    return AIResponse(
        status=status,
        response_text=response_text,
        provider_used=str(provider_used) if provider_used is not None else None,
        model_used=str(model_used) if model_used is not None else None,
        is_personalized=True,
        red_flags_detected=red_flags.get("has_urgent_symptoms", False),
        urgency_level=red_flags.get("urgency_level", "ROUTINE"),
        emergency_escalation_message=red_flags.get("escalation_message") if red_flags.get("has_urgent_symptoms") else None,
        missing_data_noted=list(context.missing_data_summary),
        citations=list(CANONICAL_CITATIONS),
        deterministic_insights={
            "bmi": context.profile.calculated_bmi,
            "cycle_rhythm": context.cycles.statistics.get("rhythm_classification"),
            "rotterdam_phenotype": context.clinical.rotterdam_assessment.get("educational_phenotype_alignment"),
            "abnormal_biomarkers_count": len(context.labs.abnormal_biomarkers),
        },
        disclaimer=STANDARD_DISCLAIMER,
    )


def generate_copilot_response(
    db: Session,
    user: User,
    request: AICopilotRequest,
) -> AIResponse:
    """Generate targeted guidance for daily coaching, symptom checks, or lab reviews."""
    context = build_user_health_context(db=db, user=user)

    action_prompts = {
        "daily_briefing": (
            "Provide a brief, supportive daily health briefing based on recent symptoms and lifestyle logs. "
            "Highlight consistent habits and suggest 1-2 practical, evidence-based focus points for today."
        ),
        "symptom_check": (
            "Review recently reported symptoms and evaluate symptom trends. "
            "Explain possible underlying hormonal drivers educationally without making a diagnosis."
        ),
        "lab_review": (
            "Review all recorded laboratory biomarkers. Explain the clinical purpose of each test, "
            "compare against laboratory reference intervals, and list critical PCOS tests that have not yet been performed."
        ),
        "lifestyle_coaching": (
            "Provide actionable lifestyle coaching focusing on sleep hygiene, stress reduction, and Low-GI nutrition. "
            "Reference the Monash 2023 international guideline recommendations for lifestyle interventions in PCOS."
        ),
        "consultation_packet": (
            "Prepare a structured, professional clinical appointment preparation packet. "
            "Include: (1) Patient summary with documented biometrics, cycle rhythm, and out-of-range lab markers; "
            "(2) 4-5 high-yield clinical discussion questions tailored to this specific patient's data gaps and symptoms; "
            "(3) Recommended follow-up diagnostic or metabolic evaluations to ask the doctor about."
        ),
    }

    instruction = action_prompts.get(request.action, action_prompts["daily_briefing"])
    if request.user_query:
        instruction += f"\nSpecific user request: {request.user_query}"

    prompt = (
        f"{context.to_clinical_prompt_text()}\n\n"
        f"## COPILOT TASK: {request.action.upper()}\n"
        f"{instruction}\n\n"
        f"Be concise, actionable, and strictly adhere to authentic records."
    )

    red_flags = context.symptoms.red_flag_screening
    provider_used: Optional[str] = None
    model_used: Optional[str] = None
    response_text = ""
    status = "success"

    try:
        response_text, provider_used, model_used = _dispatch_ai_request(prompt=prompt)
    except AIEngineError as exc:
        logger.warning("AI providers failed for copilot (%s). Engaging deterministic fallback.", exc)
        response_text = _generate_deterministic_clinical_fallback(
            user_query=f"Copilot: {request.action}",
            context=context,
            red_flags=red_flags,
        )
        provider_used = "deterministic_fallback"
        model_used = "clinical_rule_engine"
        status = "partial_deterministic"

    if red_flags.get("has_urgent_symptoms"):
        status = "emergency_escalation"
        response_text = (
            f"> [!CAUTION]\n> **URGENT MEDICAL NOTICE**: {red_flags.get('escalation_message')}\n\n"
            + response_text
        )

    return AIResponse(
        status=status,
        response_text=response_text,
        provider_used=str(provider_used) if provider_used is not None else None,
        model_used=str(model_used) if model_used is not None else None,
        is_personalized=True,
        red_flags_detected=red_flags.get("has_urgent_symptoms", False),
        urgency_level=red_flags.get("urgency_level", "ROUTINE"),
        emergency_escalation_message=red_flags.get("escalation_message") if red_flags.get("has_urgent_symptoms") else None,
        missing_data_noted=list(context.missing_data_summary),
        citations=list(CANONICAL_CITATIONS),
        deterministic_insights={
            "action": request.action,
            "cycle_rhythm": context.cycles.statistics.get("rhythm_classification"),
            "rotterdam_phenotype": context.clinical.rotterdam_assessment.get("educational_phenotype_alignment"),
        },
        disclaimer=STANDARD_DISCLAIMER,
    )
