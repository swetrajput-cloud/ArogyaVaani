from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.database import Base
from datetime import datetime

class Admission(Base):
    __tablename__ = "admissions"

    id            = Column(Integer, primary_key=True, index=True)
    patient_id    = Column(Integer, ForeignKey("patients.id"), nullable=False)
    call_sid      = Column(String, nullable=True)
    reason        = Column(Text, nullable=True)
    risk_tier     = Column(String, default="RED")
    status        = Column(String, default="pending")  # pending, admitted, discharged
    requested_at  = Column(DateTime, default=datetime.utcnow)
    admitted_at   = Column(DateTime, nullable=True)
    discharged_at = Column(DateTime, nullable=True)
    notes         = Column(Text, nullable=True)

    patient = relationship("Patient", backref="admissions")