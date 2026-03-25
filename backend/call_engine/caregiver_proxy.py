from models.patient import Patient

def should_use_caregiver(patient: Patient) -> bool:
    """
    Route call to caregiver if:
    - Patient age >= 65, OR
    - caregiver_primary is True
    """
    if patient.caregiver_primary:
        return True
    if patient.age and patient.age >= 65:
        return True
    return False

def get_caregiver_number(patient: Patient) -> str | None:
    """Return caregiver phone if available."""
    return patient.caregiver_phone if patient.caregiver_phone else None