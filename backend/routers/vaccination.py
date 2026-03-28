from fastapi import APIRouter, Query
from models.database import SessionLocal
from models.vaccination import VaccinationSchedule
from modules.vaccination import AGE_LABEL_TO_WEEKS

router = APIRouter(prefix="/vaccination", tags=["vaccination"])

@router.get("/schedule")
def get_full_schedule():
    """Return complete vaccination schedule."""
    db = SessionLocal()
    try:
        records = db.query(VaccinationSchedule).order_by(
            VaccinationSchedule.age_weeks
        ).all()
        return {
            "total": len(records),
            "schedule": [
                {
                    "id": r.id,
                    "age_label": r.age_label,
                    "age_weeks": r.age_weeks,
                    "vaccine_name": r.vaccine_name,
                    "dose": r.dose,
                    "route_site": r.route_site,
                    "remarks": r.remarks,
                }
                for r in records
            ]
        }
    finally:
        db.close()

@router.get("/due")
def get_due_vaccines(age_weeks: int = Query(...)):
    """Return vaccines due at a specific age in weeks."""
    db = SessionLocal()
    try:
        records = db.query(VaccinationSchedule).filter(
            VaccinationSchedule.age_weeks == age_weeks
        ).all()
        return {
            "age_weeks": age_weeks,
            "vaccines": [
                {
                    "vaccine_name": r.vaccine_name,
                    "dose": r.dose,
                    "route_site": r.route_site,
                    "remarks": r.remarks,
                }
                for r in records
            ]
        }
    finally:
        db.close()

@router.get("/by-age-label")
def get_by_age_label(age: str = Query(...)):
    """Get vaccines by age label e.g. '6 weeks'"""
    db = SessionLocal()
    try:
        records = db.query(VaccinationSchedule).filter(
            VaccinationSchedule.age_label == age
        ).all()
        return {
            "age_label": age,
            "vaccines": [
                {
                    "vaccine_name": r.vaccine_name,
                    "dose": r.dose,
                    "route_site": r.route_site,
                    "remarks": r.remarks,
                }
                for r in records
            ]
        }
    finally:
        db.close()