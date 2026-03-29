from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Base

class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)

    # Basic info
    name = Column(String, nullable=False)
    phone = Column(String, nullable=False, unique=True)
    age = Column(Integer, nullable=True)
    language = Column(String, default="hindi")

    # Health camp source
    health_camp_name = Column(String, nullable=True)

    # Condition + module
    condition = Column(String, nullable=False)
    module_type = Column(String, nullable=False)

    # Vitals
    systolic_bp = Column(Float, nullable=True)
    diastolic_bp = Column(Float, nullable=True)
    heart_rate = Column(Float, nullable=True)
    respiratory_rate = Column(Float, nullable=True)
    oxygen_saturation = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    blood_glucose = Column(Float, nullable=True)
    height = Column(Float, nullable=True)
    weight = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    waist_circumference = Column(Float, nullable=True)
    perfusion_index = Column(Float, nullable=True)
    waist_to_height_ratio = Column(Float, nullable=True)
    bmi_category = Column(String, nullable=True)

    # Risk scores
    heart_risk_total_score = Column(Float, nullable=True)
    heart_risk_level = Column(String, nullable=True)
    diabetic_risk_total_score = Column(Float, nullable=True)
    diabetic_risk_level = Column(String, nullable=True)
    hypertension_risk_total_score = Column(Float, nullable=True)
    hypertension_risk_level = Column(String, nullable=True)
    overall_risk_score = Column(Float, nullable=True)

    # Symptoms
    chest_discomfort = Column(String, nullable=True)
    breathlessness = Column(String, nullable=True)
    palpitations = Column(String, nullable=True)
    fatigue_weakness = Column(String, nullable=True)
    dizziness_blackouts = Column(String, nullable=True)

    # Lifestyle
    sleep_duration = Column(String, nullable=True)
    stress_anxiety = Column(String, nullable=True)
    physical_inactivity = Column(String, nullable=True)
    diet_quality = Column(String, nullable=True)
    family_history = Column(String, nullable=True)

    # Caregiver
    caregiver_primary = Column(Boolean, default=False)
    caregiver_name = Column(String, nullable=True)
    caregiver_phone = Column(String, nullable=True)

    # Risk tier
    current_risk_tier = Column(String, default="GREEN")

    # Follow-up tracking
    last_called_at = Column(DateTime, nullable=True)

    # Metadata
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)