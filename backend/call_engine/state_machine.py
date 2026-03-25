from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, List

class CallState(str, Enum):
    IDLE = "IDLE"
    DIALING = "DIALING"
    GREETING = "GREETING"
    QUESTIONING = "QUESTIONING"
    PROCESSING = "PROCESSING"
    COMPLETE = "COMPLETE"
    FAILED = "FAILED"

@dataclass
class CallSession:
    call_sid: str
    patient_id: int
    module_type: str
    language: str
    state: CallState = CallState.IDLE
    question_index: int = 0
    transcript_parts: List[str] = field(default_factory=list)
    nlp_outputs: List[dict] = field(default_factory=list)
    risk_tier: str = "GREEN"
    escalate_flag: bool = False
    escalation_reason: str = ""
    answered_by: str = "patient"

    def add_transcript(self, text: str):
        self.transcript_parts.append(text)

    def full_transcript(self) -> str:
        return " | ".join(self.transcript_parts)

    def advance_question(self):
        self.question_index += 1

    def transition(self, new_state: CallState):
        print(f"[StateMachine] {self.call_sid}: {self.state} → {new_state}")
        self.state = new_state

# In-memory session store (keyed by call_sid)
_sessions: dict[str, CallSession] = {}

def create_session(call_sid: str, patient_id: int, module_type: str, language: str) -> CallSession:
    session = CallSession(
        call_sid=call_sid,
        patient_id=patient_id,
        module_type=module_type,
        language=language,
        state=CallState.DIALING,
    )
    _sessions[call_sid] = session
    return session

def get_session(call_sid: str) -> Optional[CallSession]:
    return _sessions.get(call_sid)

def delete_session(call_sid: str):
    _sessions.pop(call_sid, None)