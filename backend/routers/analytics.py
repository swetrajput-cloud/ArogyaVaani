from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
from models.database import SessionLocal
from models.call_record import CallRecord
from models.patient import Patient
from models.appointment import Appointment
from datetime import datetime, timedelta

router = APIRouter(prefix="/analytics", tags=["analytics"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    total_calls   = db.query(CallRecord).count()
    total_patients = db.query(Patient).count()
    escalated     = db.query(CallRecord).filter(CallRecord.escalate_flag == True).count()
    appointments  = db.query(Appointment).count()
    confirmed     = db.query(Appointment).filter(Appointment.status == "confirmed").count()

    red   = db.query(CallRecord).filter(CallRecord.risk_tier == "RED").count()
    amber = db.query(CallRecord).filter(CallRecord.risk_tier == "AMBER").count()
    green = db.query(CallRecord).filter(CallRecord.risk_tier == "GREEN").count()

    return {
        "total_calls":      total_calls,
        "total_patients":   total_patients,
        "escalated":        escalated,
        "appointments":     appointments,
        "confirmed_appointments": confirmed,
        "risk_distribution": {"RED": red, "AMBER": amber, "GREEN": green},
    }

@router.get("/calls-over-time")
def calls_over_time(days: int = 7, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            cast(CallRecord.created_at, Date).label("date"),
            CallRecord.risk_tier,
            func.count().label("count"),
        )
        .filter(CallRecord.created_at >= since)
        .group_by(cast(CallRecord.created_at, Date), CallRecord.risk_tier)
        .order_by(cast(CallRecord.created_at, Date))
        .all()
    )

    # Build date → {RED, AMBER, GREEN} map
    data = {}
    for row in rows:
        d = str(row.date)
        if d not in data:
            data[d] = {"date": d, "RED": 0, "AMBER": 0, "GREEN": 0, "total": 0}
        data[d][row.risk_tier] = row.count
        data[d]["total"] += row.count

    # Fill missing dates with zeros
    result = []
    for i in range(days):
        d = str((since + timedelta(days=i+1)).date())
        result.append(data.get(d, {"date": d, "RED": 0, "AMBER": 0, "GREEN": 0, "total": 0}))

    return {"data": result}

@router.get("/top-symptoms")
def top_symptoms(db: Session = Depends(get_db)):
    rows = (
        db.query(CallRecord.structured_output)
        .filter(CallRecord.structured_output != None)
        .limit(200)
        .all()
    )

    symptom_count = {}
    topic_count = {}

    for (output,) in rows:
        if not output:
            continue
        # Count topics
        topic = output.get("topic", "")
        if topic and topic not in ("unknown", "general", ""):
            topic_count[topic] = topic_count.get(topic, 0) + 1
        # Count symptoms
        symptoms = output.get("structured_answer", {}).get("symptoms", [])
        for s in symptoms:
            if s:
                s = s.lower().strip()
                symptom_count[s] = symptom_count.get(s, 0) + 1

    top_topics = sorted(topic_count.items(), key=lambda x: x[1], reverse=True)[:8]
    top_symptoms = sorted(symptom_count.items(), key=lambda x: x[1], reverse=True)[:8]

    return {
        "topics":   [{"name": k, "count": v} for k, v in top_topics],
        "symptoms": [{"name": k, "count": v} for k, v in top_symptoms],
    }

@router.get("/escalation-rate")
def escalation_rate(days: int = 7, db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=days)
    rows = (
        db.query(
            cast(CallRecord.created_at, Date).label("date"),
            func.count().label("total"),
            func.sum(func.cast(CallRecord.escalate_flag, db.bind.dialect.name == 'sqlite' and 'INTEGER' or 'INTEGER')).label("escalated"),
        )
        .filter(CallRecord.created_at >= since)
        .group_by(cast(CallRecord.created_at, Date))
        .order_by(cast(CallRecord.created_at, Date))
        .all()
    )

    result = []
    for row in rows:
        total = row.total or 0
        esc   = int(row.escalated or 0)
        result.append({
            "date":      str(row.date),
            "total":     total,
            "escalated": esc,
            "rate":      round((esc / total * 100), 1) if total else 0,
        })

    return {"data": result}