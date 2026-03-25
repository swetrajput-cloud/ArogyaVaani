from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

# --- Patient Schemas ---
class PatientCreate(BaseModel):
    name: str
    phone: str
    age: int
    language: str = "hindi"
    condition: str
    module_type: str
    caregiver_primary: bool = False
    caregiver_name: Optional[str] = None
    caregiver_phone: Optional[str] = None

class PatientResponse(BaseModel):
    id: int
    name: str
    phone: str
    age: int
    language: str
    condition: str
    module_type: str
    caregiver_primary: bool
    caregiver_name: Optional[str]
    caregiver_phone: Optional[str]
    current_risk_tier: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

# --- Call Record Schemas ---
class CallRecordCreate(BaseModel):
    patient_id: int
    module_type: str
    language: str

class CallRecordResponse(BaseModel):
    id: int
    patient_id: int
    call_sid: Optional[str]
    module_type: str
    language: str
    transcript: Optional[str]
    structured_output: Optional[Dict[str, Any]]
    risk_tier: str
    escalate_flag: bool
    escalation_reason: Optional[str]
    adherence_score: Optional[float]
    answered_by: str
    call_status: str
    call_duration: Optional[int]
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True

# --- NLP Output Schema ---
class NLPOutput(BaseModel):
    topic: str
    sentiment: str
    severity: int  # 1-5
    keywords: List[str]
    structured_answer: Dict[str, Any]

# --- Risk Assessment Schema ---
class RiskAssessment(BaseModel):
    risk_tier: str  # GREEN, AMBER, RED
    escalate_flag: bool
    escalation_reason: Optional[str]
    detected_keywords: List[str]