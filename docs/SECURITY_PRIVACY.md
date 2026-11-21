# PCOS360 — Security & Privacy Architecture

## 1. Threat Model & Clinical Privacy Commitments

PCOS360 handles sensitive reproductive and metabolic health data. The architecture adheres to five fundamental commitments:
1. **Zero Data Fabrication**: Patient health parameters, lab values, and symptom correlations are never invented or simulated for authenticated users.
2. **Strict User Isolation**: All database queries and context pipelines filter exclusively by the cryptographically verified user identity.
3. **No Unconsented Third-Party Training**: Patient health records are de-identified before dispatch to external LLMs and are not used for public model training.
4. **Instant Session Revocation**: Logging out marks the server-side session revoked in PostgreSQL, immediately invalidating the JWT across all devices.
5. **Clear Medical Disclaimers**: The platform explicitly informs users that all analytical discoveries and AI outputs are educational decision-support tools and not clinical diagnoses.

---

## 2. Authentication & Credential Storage

- **Password Storage**: Passwords are never stored in plaintext. They are salted and hashed using `scrypt` or `bcrypt` via Passlib's `CryptContext`.
- **Timing Attack Mitigation**: When a non-existent email is queried during login, the system runs a constant-time dummy password verification routine to prevent timing-based user enumeration.
- **JWT Lifecycles**: Tokens are signed using HMAC-SHA256 with a cryptographically generated 256-bit secret key. Each token includes an ephemeral `jti` (JWT ID).
- **Server-Side Session Store**: Tokens are tracked in the `user_sessions` database table. On every API request, the server verifies:
  1. Valid cryptographic signature.
  2. Token has not expired (`expires_at > now()`).
  3. Session has not been revoked (`revoked_at IS NULL`).
  4. User account is active and not marked as demo.

---

## 3. Network & Transport Security

- **Enforced HTTPS**: All communication between clients and the Render backend uses TLS 1.3 encryption.
- **Strict CORS Policy**: Whitelists authorized frontend client origins. Prohibits wildcard (`*`) access in production environments.
- **Rate Limiting**: Sliding-window rate limiters restrict authentication attempts:
  - Account Sign-in: Max 5 failed attempts per 300 seconds.
  - IP Sign-in: Max 20 attempts per 300 seconds.
  - Registration: Max 10 attempts per 300 seconds.

---

## 4. AI Guardrails & Sensitive Data Protection

- **Red-Flag Screening**: Before executing any AI generation, input text is evaluated against deterministic emergency keywords (acute pelvic pain, severe bleeding, fainting). If triggered, the request bypasses the LLM and delivers an immediate emergency escalation notice.
- **API Key Secrecy**: External AI provider keys (`GEMINI_API_KEY`, `GROQ_API_KEY`) reside exclusively in server-side environment variables and are never transmitted to clients.
- **Audit Logging Hygiene**: Server logs strictly record operational metadata (endpoint, status code, latency). Patient names, health values, cycle dates, and authentication tokens are strictly excluded from logs.

