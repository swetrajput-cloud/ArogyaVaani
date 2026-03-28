from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from models.database import Base
from datetime import datetime

class Appointment(Base):
    __tablename__ = "appointments"

    id           = Column(Integer, primary_key=True, index=True)
    patient_id   = Column(Integer, ForeignKey("patients.id"), nullable=False)
    call_sid     = Column(String, nullable=True)
    reason       = Column(Text, nullable=True)
    status       = Column(String, default="pending")  # pending, confirmed, rejected
    requested_at = Column(DateTime, default=datetime.utcnow)
    confirmed_at = Column(DateTime, nullable=True)
    notes        = Column(Text, nullable=True)

    patient = relationship("Patient", backref="appointments")