# PCOS360 — Known Limitations & Scope Boundaries

## 1. Clinical Scope & Regulatory Boundaries

1. **Not a Medical Device**: PCOS360 is an educational health intelligence and tracking platform. It is not an FDA/CE-cleared Software as a Medical Device (SaMD) and does not provide automated diagnoses, clinical prognoses, or prescription recommendations.
2. **Unconfirmed Ovulation Status**: Calendar-based menstrual cycle predictions cannot confirm physiological ovulation. True ovulation confirmation requires serial transvaginal follicular tracking, mid-luteal serum progesterone assays ($\ge 3$ ng/mL), or biphasic basal body temperature shifts.
3. **Statistical Sample Size Constraints**: Pearson correlations require a minimum of 7 paired observation days ($N \ge 7$). Statistical associations identified by the system do not imply direct clinical causality.
4. **Rotterdam Decision-Support**: Educational Rotterdam assessment requires at least two completed cycles, biochemical androgen measurements, and pelvic ultrasound imaging. Missing diagnostic modalities are explicitly flagged and cannot be inferred by the AI.

---

## 2. Technical & Infrastructure Limitations

1. **Free-Tier Render Hibernation**: When hosted on Render's free tier, the backend web service enters hibernation after 15 minutes of inactivity. Initial wake-up requests may experience a 30–50 second cold start delay. Subsequent requests respond in under 200 milliseconds.
2. **Cross-Continent Database Latency**: Connecting from developer machines outside the Asia-Pacific region to the Supabase PostgreSQL instance in AWS Tokyo introduces approximately 150–250 ms of network latency per round trip.
3. **AI Provider Availability**: While Google Gemini Flash-Lite is the primary provider with automated fallback to Groq Llama-3.3-70b and deterministic rule-based engines, unexpected global API outages or rate limit exhaustion may briefly restrict AI narrative generation. Deterministic calculators remain available at all times.
4. **Physical Device USB Verification**: Automatic ADB-driven end-to-end device testing is contingent upon physical hardware connection to the host workstation. Manual verification via the APK installation guide is recommended for release sign-off.

