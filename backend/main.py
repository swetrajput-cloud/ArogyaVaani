from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import sys, os, csv
from datetime import datetime, date as dt_date

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from models.database import create_tables, SessionLocal
from models.patient import Patient
from call_engine.twiml_router import router as twilio_router
from dashboard.ws_broadcaster import connect_client, disconnect_client
from call_engine.media_stream import handle_media_stream

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(twilio_router)

# ─── WebSocket: Live Dashboard ────────────────────────────────────────────────
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await connect_client(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        disconnect_client(websocket)

# ─── WebSocket: Twilio Media Stream ──────────────────────────────────────────
@app.websocket("/ws/stream/{call_sid}")
async def media_stream_ws(websocket: WebSocket, call_sid: str):
    await handle_media_stream(websocket, call_sid)

# ─── CSV Seeding ──────────────────────────────────────────────────────────────
CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "patients.csv")

def safe_float(val):
    try:
        return float(val)
    except:
        return None

def safe_str(val):
    v = val.strip() if val else None
    return None if v in ("", "null", "NULL", "None") else v

def map_risk_tier(overall_risk_category: str) -> str:
    mapping = {"Low": "GREEN", "Moderate": "AMBER", "High": "RED"}
    return mapping.get(overall_risk_category.strip(), "GREEN")

def derive_module(row: dict) -> str:
    camp = row.get("health_camp_name", "").lower()
    if "old age" in camp:
        return "post_discharge"
    if "deaddiction" in camp or "disha" in camp:
        return "chronic_coach"
    return "post_discharge"

def derive_condition(row: dict) -> str:
    parts = []
    if row.get("heart_risk_level", "").strip() == "High":
        parts.append("Heart Disease")
    if row.get("diabetic_risk_level", "").strip() == "High":
        parts.append("Diabetes")
    if row.get("hypertension_risk_level", "").strip() == "High":
        parts.append("Hypertension")
    return ", ".join(parts) if parts else "General Monitoring"

def seed_patients_from_csv():
    if not os.path.exists(CSV_PATH):
        print(f"[Seed] CSV not found at {CSV_PATH}, skipping.")
        return
    db = SessionLocal()
    try:
        existing = db.query(Patient).count()
        if existing > 0:
            print(f"[Seed] DB already has {existing} patients, skipping CSV seed.")
            return
        with open(CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            patients = []
            for i, row in enumerate(reader, start=1):
                risk_tier = map_risk_tier(row.get("overall_risk_category", ""))
                patient = Patient(
                    name=f"Patient #{i}",
                    phone=f"+910000{i:05d}",
                    age=None,
                    language="hindi",
                    health_camp_name=safe_str(row.get("health_camp_name")),
                    visit_date=dt_date.today(),
                    condition=derive_condition(row),
                    module_type=derive_module(row),
                    systolic_bp=safe_float(row.get("systolic_bp", "")),
                    diastolic_bp=safe_float(row.get("diastolic_bp", "")),
                    heart_rate=safe_float(row.get("heart_rate", "")),
                    respiratory_rate=safe_float(row.get("respiratory_rate", "")),
                    oxygen_saturation=safe_float(row.get("oxygen_saturation", "")),
                    temperature=safe_float(row.get("temperature", "")),
                    blood_glucose=safe_float(row.get("blood_glucose", "")),
                    height=safe_float(row.get("height", "")),
                    weight=safe_float(row.get("weight", "")),
                    bmi=safe_float(row.get("bmi", "")),
                    waist_circumference=safe_float(row.get("waist_circumference", "")),
                    perfusion_index=safe_float(row.get("perfusion_index", "")),
                    waist_to_height_ratio=safe_float(row.get("waist_to_height_ratio", "")),
                    bmi_category=safe_str(row.get("bmi_category")),
                    heart_risk_total_score=safe_float(row.get("heart_risk_total_score", "")),
                    heart_risk_level=safe_str(row.get("heart_risk_level")),
                    diabetic_risk_total_score=safe_float(row.get("diabetic_risk_total_score", "")),
                    diabetic_risk_level=safe_str(row.get("diabetic_risk_level")),
                    hypertension_risk_total_score=safe_float(row.get("hypertension_risk_total_score", "")),
                    hypertension_risk_level=safe_str(row.get("hypertension_risk_level")),
                    overall_risk_score=safe_float(row.get("overall_risk_score", "")),
                    chest_discomfort=safe_str(row.get("chest_discomfort")),
                    breathlessness=safe_str(row.get("breathlessness")),
                    palpitations=safe_str(row.get("palpitations")),
                    fatigue_weakness=safe_str(row.get("fatigue_weakness")),
                    dizziness_blackouts=safe_str(row.get("dizziness_blackouts")),
                    sleep_duration=safe_str(row.get("sleep_duration")),
                    stress_anxiety=safe_str(row.get("stress_anxiety")),
                    physical_inactivity=safe_str(row.get("physical_inactivity")),
                    diet_quality=safe_str(row.get("diet_quality")),
                    family_history=safe_str(row.get("family_history")),
                    current_risk_tier=risk_tier,
                    caregiver_primary=False,
                )
                patients.append(patient)
            db.bulk_save_objects(patients)
            db.commit()
            print(f"[Seed] ✅ Seeded {len(patients)} patients from CSV.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] ❌ CSV seed failed: {e}")
    finally:
        db.close()

# ─── Patient API Routes ───────────────────────────────────────────────────────
@app.get('/patients')
def get_patients(
    risk_tier: Optional[str] = Query(None),
    health_camp: Optional[str] = Query(None),
    limit: int = Query(50, le=120),
    offset: int = Query(0)
):
    db = SessionLocal()
    try:
        query = db.query(Patient).filter(Patient.is_active == True)
        if risk_tier:
            query = query.filter(Patient.current_risk_tier == risk_tier.upper())
        if health_camp:
            query = query.filter(Patient.health_camp_name == health_camp)
        total = query.count()
        # Sort by visit_date newest first
        patients = query.order_by(
            Patient.visit_date.desc().nullslast(),
            Patient.created_at.desc().nullslast()
        ).offset(offset).limit(limit).all()
        return {
            "total": total,
            "patients": [
                {
                    "id": p.id,
                    "name": p.name,
                    "phone": p.phone,
                    "age": p.age,
                    "language": p.language,
                    "health_camp_name": p.health_camp_name,
                    "visit_date": p.visit_date.isoformat() if p.visit_date else None,
                    "condition": p.condition,
                    "module_type": p.module_type,
                    "current_risk_tier": p.current_risk_tier,
                    "heart_risk_level": p.heart_risk_level,
                    "diabetic_risk_level": p.diabetic_risk_level,
                    "hypertension_risk_level": p.hypertension_risk_level,
                    "overall_risk_score": p.overall_risk_score,
                    "bmi": p.bmi,
                    "systolic_bp": p.systolic_bp,
                    "diastolic_bp": p.diastolic_bp,
                    "blood_glucose": p.blood_glucose,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                }
                for p in patients
            ]
        }
    finally:
        db.close()

@app.get('/patients/{patient_id}')
def get_patient(patient_id: int):
    from fastapi import HTTPException
    db = SessionLocal()
    try:
        p = db.query(Patient).filter(Patient.id == patient_id).first()
        if not p:
            raise HTTPException(status_code=404, detail="Patient not found")
        return {
            "id": p.id, "name": p.name, "phone": p.phone, "age": p.age,
            "language": p.language, "health_camp_name": p.health_camp_name,
            "visit_date": p.visit_date.isoformat() if p.visit_date else None,
            "condition": p.condition, "module_type": p.module_type,
            "current_risk_tier": p.current_risk_tier,
            "systolic_bp": p.systolic_bp, "diastolic_bp": p.diastolic_bp,
            "heart_rate": p.heart_rate, "respiratory_rate": p.respiratory_rate,
            "oxygen_saturation": p.oxygen_saturation, "temperature": p.temperature,
            "blood_glucose": p.blood_glucose, "height": p.height, "weight": p.weight,
            "bmi": p.bmi, "bmi_category": p.bmi_category,
            "waist_circumference": p.waist_circumference,
            "heart_risk_level": p.heart_risk_level,
            "heart_risk_total_score": p.heart_risk_total_score,
            "diabetic_risk_level": p.diabetic_risk_level,
            "diabetic_risk_total_score": p.diabetic_risk_total_score,
            "hypertension_risk_level": p.hypertension_risk_level,
            "hypertension_risk_total_score": p.hypertension_risk_total_score,
            "overall_risk_score": p.overall_risk_score,
            "chest_discomfort": p.chest_discomfort, "breathlessness": p.breathlessness,
            "palpitations": p.palpitations, "fatigue_weakness": p.fatigue_weakness,
            "dizziness_blackouts": p.dizziness_blackouts,
            "sleep_duration": p.sleep_duration, "stress_anxiety": p.stress_anxiety,
            "physical_inactivity": p.physical_inactivity, "diet_quality": p.diet_quality,
            "family_history": p.family_history,
            "caregiver_primary": p.caregiver_primary,
            "caregiver_name": p.caregiver_name, "caregiver_phone": p.caregiver_phone,
            "is_active": p.is_active,
            "created_at": p.created_at.isoformat() if p.created_at else None,
        }
    finally:
        db.close()

@app.get('/stats')
def get_stats():
    db = SessionLocal()
    try:
        total = db.query(Patient).count()
        red   = db.query(Patient).filter(Patient.current_risk_tier == "RED").count()
        amber = db.query(Patient).filter(Patient.current_risk_tier == "AMBER").count()
        green = db.query(Patient).filter(Patient.current_risk_tier == "GREEN").count()
        return {"total_patients": total, "red": red, "amber": amber, "green": green}
    finally:
        db.close()

# ─── Call Simulator ───────────────────────────────────────────────────────────
class SimulateRequest(BaseModel):
    patient_id: int
    transcript: str
    language: str = "hindi"

@app.post('/simulate/call')
async def simulate_call(req: SimulateRequest):
    from nlp.intent_extractor import extract_intent
    from nlp.risk_scorer import compute_risk
    from dashboard.ws_broadcaster import broadcast_update
    db = SessionLocal()
    try:
        from fastapi import HTTPException
        patient = db.query(Patient).filter(Patient.id == req.patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")
        nlp_output = await extract_intent(req.transcript, req.language)
        risk_tier, escalate, reason, keywords = compute_risk(
            req.transcript, nlp_output, patient.overall_risk_score or 0
        )
        patient.current_risk_tier = risk_tier
        patient.updated_at = datetime.utcnow()
        db.commit()
        await broadcast_update({
            "call_sid": f"SIM-{req.patient_id}-{int(datetime.utcnow().timestamp())}",
            "patient_id": req.patient_id, "patient_name": patient.name,
            "risk_tier": risk_tier, "escalate": escalate,
            "escalation_reason": reason, "transcript": req.transcript,
            "keywords": keywords, "nlp": nlp_output,
        })
        return {
            "patient_id": req.patient_id, "patient_name": patient.name,
            "transcript": req.transcript, "nlp": nlp_output,
            "risk_tier": risk_tier, "escalate": escalate,
            "escalation_reason": reason, "keywords": keywords,
        }
    finally:
        db.close()

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event('startup')
async def startup():
    create_tables()
    print("[Startup] Database tables created successfully")
    seed_patients_from_csv()

@app.get('/')
def root():
    return {"message": f"{settings.APP_NAME} backend is running", "debug": settings.DEBUG}

@app.get('/health')
def health():
    return {"status": "ok"}