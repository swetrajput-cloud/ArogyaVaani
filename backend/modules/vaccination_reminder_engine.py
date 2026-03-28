from datetime import date, timedelta
from models.database import SessionLocal
from models.patient import Patient
from models.vaccination import VaccinationSchedule
from models.vaccination_reminder import VaccinationReminder
from sqlalchemy import and_

def get_reminders_due_today():
    """Return all reminders where reminder_date == today and status == pending."""
    db = SessionLocal()
    try:
        today = date.today()
        reminders = db.query(VaccinationReminder).filter(
            and_(
                VaccinationReminder.reminder_date == today,
                VaccinationReminder.call_status == "pending"
            )
        ).all()
        return [
            {
                "id":            r.id,
                "patient_id":    r.patient_id,
                "patient_name":  r.patient_name,
                "patient_phone": r.patient_phone,
                "vaccine_name":  r.vaccine_name,
                "age_label":     r.age_label,
                "due_date":      str(r.due_date),
            }
            for r in reminders
        ]
    finally:
        db.close()


def create_reminders_for_patient(patient_id: int, baby_dob: date):
    """
    Given a patient and their baby's DOB, generate reminders
    for all vaccination milestones, 7 days before due date.
    """
    db = SessionLocal()
    try:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return {"error": "Patient not found"}

        schedules = db.query(VaccinationSchedule).all()

        weeks_to_days = {
            0:  0,
            6:  42,
            10: 70,
            14: 98,
            36: 252,
            52: 364,
        }

        created = 0
        for s in schedules:
            days_offset = weeks_to_days.get(s.age_weeks)
            if days_offset is None:
                continue

            due_date      = baby_dob + timedelta(days=days_offset)
            reminder_date = due_date - timedelta(days=7)

            # Skip if already in past
            if reminder_date < date.today():
                continue

            # Skip duplicates
            exists = db.query(VaccinationReminder).filter(
                and_(
                    VaccinationReminder.patient_id == patient_id,
                    VaccinationReminder.vaccine_name == s.vaccine_name,
                    VaccinationReminder.due_date == due_date,
                )
            ).first()
            if exists:
                continue

            reminder = VaccinationReminder(
                patient_id    = patient_id,
                patient_name  = patient.name,
                patient_phone = patient.phone,
                vaccine_name  = s.vaccine_name,
                age_label     = s.age_label,
                due_date      = due_date,
                reminder_date = reminder_date,
                call_status   = "pending",
            )
            db.add(reminder)
            created += 1

        db.commit()
        return {"created": created, "patient_id": patient_id}

    except Exception as e:
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()


def mark_reminder_called(reminder_id: int, call_sid: str, status: str = "called"):
    from datetime import datetime
    db = SessionLocal()
    try:
        r = db.query(VaccinationReminder).filter(VaccinationReminder.id == reminder_id).first()
        if r:
            r.call_status = status
            r.call_sid    = call_sid
            r.called_at   = datetime.utcnow()
            db.commit()
    finally:
        db.close()