import os
import sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.abspath('backend'))
load_dotenv('backend/.env')

from app.core.database import SessionLocal
from app.models.user import User
from app.models.health_profile import HealthProfile
from app.models.menstrual_cycle import MenstrualCycle
from app.models.daily_symptom import DailySymptom
from app.models.lifestyle_log import LifestyleLog
from app.models.lab_report import LabReport

with SessionLocal() as db:
    user = db.query(User).filter(User.email == 'ananya.qa7@pcos360-real.org').first()
    if not user:
        print("User not found!")
    else:
        print(f"User: id={user.id}, name={user.full_name}, email={user.email}")
        profile = db.query(HealthProfile).filter(HealthProfile.user_id == user.id).first()
        if profile:
            bmi = round(profile.weight / ((profile.height / 100) ** 2), 1) if profile.height and profile.weight else None
            print(f"Profile: age={profile.age}, height={profile.height}cm, weight={profile.weight}kg, calculated_bmi={bmi}")
        cycles = db.query(MenstrualCycle).filter(MenstrualCycle.user_id == user.id).count()
        symptoms = db.query(DailySymptom).filter(DailySymptom.user_id == user.id).count()
        lifestyle = db.query(LifestyleLog).filter(LifestyleLog.user_id == user.id).count()
        labs = db.query(LabReport).filter(LabReport.user_id == user.id).count()
        print(f"PostgreSQL Records: cycles={cycles}, symptoms={symptoms}, lifestyle={lifestyle}, labs={labs}")
