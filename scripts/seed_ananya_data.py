from datetime import date, timedelta
from app.core.database import SessionLocal
from app.models.user import User
from app.models.menstrual_cycle import MenstrualCycle
from app.models.daily_symptom import DailySymptom
from app.models.lifestyle_log import LifestyleLog
from app.models.lab_report import LabReport

with SessionLocal() as db:
    user = db.query(User).filter(User.email == "ananya.qa7@pcos360-real.org").first()
    assert user is not None, "Ananya Rao user not found!"
    print(f"Seeding longitudinal records for user {user.full_name} (id={user.id})...")

    today = date.today()

    # 1. Menstrual Cycles (3 completed cycles: 33, 34, 32 days)
    cycles = [
        MenstrualCycle(
            user_id=user.id,
            period_start_date=today - timedelta(days=99),
            period_end_date=today - timedelta(days=94),
            cycle_length=33,
            flow_intensity="Medium",
            notes="Cycle 1 - mild cramps",
        ),
        MenstrualCycle(
            user_id=user.id,
            period_start_date=today - timedelta(days=66),
            period_end_date=today - timedelta(days=61),
            cycle_length=34,
            flow_intensity="Medium",
            notes="Cycle 2 - regular flow",
        ),
        MenstrualCycle(
            user_id=user.id,
            period_start_date=today - timedelta(days=32),
            period_end_date=today - timedelta(days=27),
            cycle_length=32,
            flow_intensity="Heavy",
            notes="Cycle 3 - heavier first day",
        ),
    ]
    for c in cycles:
        db.add(c)

    # 2. Daily Symptoms & Lifestyle Logs (7 paired days with clean correlation: sleep vs fatigue)
    # Sleep 8.5 -> fatigue 2, sleep 5.0 -> fatigue 9
    sleep_fatigue = [
        (8.5, 2, 1, 1),
        (8.0, 3, 2, 1),
        (7.5, 4, 2, 2),
        (7.0, 5, 3, 2),
        (6.5, 6, 3, 3),
        (6.0, 7, 4, 3),
        (5.0, 9, 5, 4),
    ]

    for i, (sleep_h, fatigue, stress, bloat) in enumerate(sleep_fatigue):
        log_d = today - timedelta(days=6 - i)
        # Daily Symptom
        sym = DailySymptom(
            user_id=user.id,
            log_date=log_d,
            acne_severity="Moderate" if i % 2 == 0 else "Mild",
            fatigue_level=fatigue,
            bloating=bloat,
            pelvic_pain=1,
            mood="Calm" if sleep_h >= 7.5 else "Anxious",
            notes=f"QA test record for day {i+1}",
        )
        db.add(sym)

        # Lifestyle Log
        life = LifestyleLog(
            user_id=user.id,
            log_date=log_d,
            sleep_hours=sleep_h,
            stress_level=stress,
            water_intake=2.5,
            exercise_minutes=30 if sleep_h >= 7.0 else 10,
            food_habits="Balanced Low-GI",
            meal_regularity="Regular",
        )
        db.add(life)

    # 3. Lab Reports (Fasting Glucose & Total Testosterone)
    lab1 = LabReport(
        user_id=user.id,
        report_name="Metabolic Baseline Panel",
        test_name="Fasting Glucose",
        test_value=94.0,
        unit="mg/dL",
        reference_range="70-99",
        report_date=today - timedelta(days=14),
    )
    lab2 = LabReport(
        user_id=user.id,
        report_name="Endocrine Androgen Panel",
        test_name="Total Testosterone",
        test_value=68.0,
        unit="ng/dL",
        reference_range="15-45",
        report_date=today - timedelta(days=14),
    )
    db.add(lab1)
    db.add(lab2)

    db.commit()
    print("✓ Successfully seeded 3 cycles, 7 paired symptoms/lifestyle, and 2 lab reports into PostgreSQL!")
