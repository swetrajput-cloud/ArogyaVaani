from sqlalchemy import Column, Integer, String, Date, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from models.database import Base

class VaccinationReminder(Base):
    __tablename__ = "vaccination_reminders"

    id              = Column(Integer, primary_key=True, index=True)
    patient_id      = Column(Integer, ForeignKey("patients.id"), nullable=False)
    patient_name    = Column(String, nullable=False)
    patient_phone   = Column(String, nullable=False)
    vaccine_name    = Column(String, nullable=False)
    age_label       = Column(String, nullable=False)
    due_date        = Column(Date, nullable=False)
    reminder_date   = Column(Date, nullable=False)   # due_date - 7 days
    call_status     = Column(String, default="pending")  # pending/called/failed
    call_sid        = Column(String, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    called_at       = Column(DateTime, nullable=True)

    patient = relationship("Patient", backref="vaccination_reminders")