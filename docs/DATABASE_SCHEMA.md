# PCOS360 — Database Schema Documentation

## 1. Overview
PCOS360 utilizes a PostgreSQL 17 relational database hosted on Supabase (AWS Tokyo). The schema enforces strict user data isolation, referential integrity via foreign key cascades, and indexing for high-performance retrieval.

---

## 2. Entity-Relationship Diagram

```
 +--------------------+       1:N       +------------------------+
 |       users        | <-------------> |     user_sessions      |
 +--------------------+                 +------------------------+
           |
           | 1:1
           +--------------------------> |    health_profiles     |
           |
           | 1:N
           +--------------------------> |    menstrual_cycles    |
           |
           | 1:N
           +--------------------------> |     daily_symptoms     |
           |
           | 1:N
           +--------------------------> |     lifestyle_logs     |
           |
           | 1:N
           +--------------------------> |      lab_reports       |
           |
           | 1:N
           +--------------------------> |    clinical_records    |
```

---

## 3. Table Definitions

### 3.1 `users`
Stores account identities, authentication credentials, and active states.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Unique user identifier. |
| `full_name` | `VARCHAR(150)` | `NOT NULL` | User's full name. |
| `email` | `VARCHAR(255)` | `UNIQUE, NOT NULL, INDEXED` | Sign-in email address. |
| `password_hash`| `VARCHAR(255)` | `NULLABLE` | Salted scrypt / bcrypt password hash. |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE, NOT NULL` | Account active status. |
| `is_demo` | `BOOLEAN` | `DEFAULT FALSE, NOT NULL` | Flags demo / sandbox accounts. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Registration timestamp. |
| `updated_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Last update timestamp. |

### 3.2 `user_sessions`
Manages stateful JWT sessions, supporting instantaneous server-side revocation on logout.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Session identifier. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `token_jti` | `VARCHAR(64)` | `UNIQUE, NOT NULL, INDEXED` | Cryptographic JWT identifier. |
| `user_agent` | `VARCHAR(255)` | `NULLABLE` | Client browser / device user agent. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Session start time. |
| `expires_at` | `TIMESTAMPTZ`| `NOT NULL, INDEXED` | Token expiration timestamp. |
| `revoked_at` | `TIMESTAMPTZ`| `NULLABLE` | Revocation timestamp on logout. |

### 3.3 `health_profiles`
Stores baseline patient demographics, biometric attributes, and reported diagnosis.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Profile identifier. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), UNIQUE, INDEXED` | 1-to-1 link to user. |
| `age` | `INTEGER` | `NULLABLE` | Age in years. |
| `height` | `FLOAT` | `NULLABLE` | Height in cm. |
| `weight` | `FLOAT` | `NULLABLE` | Weight in kg. |
| `diagnosis_status`| `VARCHAR(100)`| `NULLABLE` | Confirmed / Suspected / Not diagnosed. |
| `diagnosis_year`| `INTEGER` | `NULLABLE` | Year of initial PCOS diagnosis. |
| `existing_conditions`| `JSON / TEXT[]`| `NULLABLE` | List of co-morbidities. |
| `medications` | `JSON / TEXT[]`| `NULLABLE` | Active prescription drugs. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Creation timestamp. |
| `updated_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Last update timestamp. |

### 3.4 `menstrual_cycles`
Logs period start and end dates for cycle length and rhythm calculations.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Record identifier. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `period_start_date`| `DATE` | `NOT NULL` | First day of menstrual bleeding. |
| `period_end_date` | `DATE` | `NULLABLE` | Last day of menstrual bleeding. |
| `cycle_length` | `INTEGER` | `NOT NULL` | Computed cycle interval in days. |
| `flow_intensity` | `VARCHAR(50)` | `NULLABLE` | Light, Medium, Heavy, Spotting. |
| `notes` | `TEXT` | `NULLABLE` | Patient cycle notes. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Record timestamp. |

### 3.5 `daily_symptoms`
Daily tracking of androgenic, metabolic, and physical PCOS symptoms.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Symptom log ID. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `log_date` | `DATE` | `NOT NULL, INDEXED` | Observation date. |
| `acne_severity`| `VARCHAR(50)` | `NULLABLE` | None, Mild, Moderate, Severe. |
| `hair_loss` | `VARCHAR(50)` | `NULLABLE` | None, Mild, Moderate, Severe. |
| `unwanted_hair_growth`| `VARCHAR(50)`| `NULLABLE` | None, Mild, Moderate, Severe. |
| `fatigue_level`| `INTEGER` | `NULLABLE` | Severity scale 1 to 10. |
| `bloating` | `INTEGER` | `NULLABLE` | Severity scale 1 to 10. |
| `pelvic_pain` | `INTEGER` | `NULLABLE` | Severity scale 1 to 10. |
| `mood` | `VARCHAR(100)`| `NULLABLE` | Mood status descriptor. |
| `notes` | `TEXT` | `NULLABLE` | Daily symptom notes. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Record timestamp. |

### 3.6 `lifestyle_logs`
Tracks daily habits paired with symptoms for Pearson correlation analysis.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Lifestyle log ID. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `log_date` | `DATE` | `NOT NULL, INDEXED` | Observation date. |
| `sleep_hours` | `FLOAT` | `NOT NULL` | Hours of sleep. |
| `stress_level` | `INTEGER` | `NOT NULL` | Stress scale 1 to 5. |
| `water_intake` | `FLOAT` | `NOT NULL` | Liters or glasses of water. |
| `exercise_minutes`| `INTEGER` | `NOT NULL, DEFAULT 0` | Exercise duration in minutes. |
| `food_habits` | `VARCHAR(150)`| `NULLABLE` | Dietary pattern descriptor. |
| `meal_regularity`| `VARCHAR(50)`| `NULLABLE` | Regular, Irregular, Intermittent. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Record timestamp. |

### 3.7 `lab_reports`
Stores laboratory test panels and biomarker measurements.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Report ID. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `report_date` | `DATE` | `NOT NULL` | Sample collection / report date. |
| `test_name` | `VARCHAR(150)`| `NOT NULL` | Test name (e.g. Total Testosterone). |
| `test_value` | `FLOAT` | `NOT NULL` | Numeric test value. |
| `unit` | `VARCHAR(50)` | `NOT NULL` | Measurement unit (e.g. ng/dL). |
| `reference_range`| `VARCHAR(100)`| `NULLABLE` | Reporting laboratory's reference range. |
| `notes` | `TEXT` | `NULLABLE` | Laboratory or physician notes. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Record timestamp. |

### 3.8 `clinical_records`
Stores clinician consultation notes, ultrasound scans, and diagnosis summaries.

| Column | Type | Constraints | Description |
| :--- | :--- | :--- | :--- |
| `id` | `INTEGER` | `PRIMARY KEY, AUTOINCREMENT` | Clinical record ID. |
| `user_id` | `INTEGER` | `FK(users.id, CASCADE), INDEXED` | Owning user. |
| `record_date` | `DATE` | `NOT NULL` | Date of clinical encounter. |
| `record_type` | `VARCHAR(100)`| `NOT NULL` | Doctor Note, Ultrasound, Prescription. |
| `provider_name`| `VARCHAR(150)`| `NULLABLE` | Clinic or doctor name. |
| `summary` | `TEXT` | `NOT NULL` | Clinical encounter summary. |
| `has_ultrasound_pcom`| `BOOLEAN` | `DEFAULT FALSE` | Polycystic ovarian morphology flag. |
| `created_at` | `TIMESTAMPTZ`| `DEFAULT now(), NOT NULL` | Record timestamp. |

