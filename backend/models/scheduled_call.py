from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Text
from datetime import datetime
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.database import Base

class ScheduledCall(Base):
    __tablename__ = "scheduled_calls"

    id             = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("patients.id"), nullable=False)
    scheduled_at   = Column(DateTime, nullable=False)        # when to fire the call
    custom_note    = Column(Text, nullable=True)             # AI mentions this naturally
    status         = Column(String, default="pending")       # pending / called / cancelled / failed
    call_sid       = Column(String, nullable=True)           # filled after call fires
    created_at     = Column(DateTime, default=datetime.utcnow)
    fired_at       = Column(DateTime, nullable=True)         # when scheduler actually fired it