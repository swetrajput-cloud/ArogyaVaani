from sqlalchemy import Column, String, Integer, Boolean, DateTime, Float, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Base

class CallRecord(Base):
    __tablename__ = "call_records"

    id = Column(Integer, primary_key=True, index=True)
    
    # Link to patient
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    
    # Call info
    call_sid = Column(String, nullable=True)  # Twilio call SID
    module_type = Column(String, nullable=False)  # which module was used
    language = Column(String, nullable=False)
    
    # Transcript + NLP output
    transcript = Column(String, nullable=True)
    structured_output = Column(JSONB, nullable=True)  # full Claude NLP output
    
    # Risk
    risk_tier = Column(String, default="GREEN")  # GREEN, AMBER, RED
    escalate_flag = Column(Boolean, default=False)
    escalation_reason = Column(String, nullable=True)
    
    # Adherence
    adherence_score = Column(Float, nullable=True)  # 0.0 to 1.0
    
    # Caregiver
    answered_by = Column(String, default="patient")  # patient or caregiver
    
    # Call status
    call_status = Column(String, default="initiated")  # initiated, completed, failed, fallback_sms
    call_duration = Column(Integer, nullable=True)  # in seconds
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)