from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys, os, csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import settings
from models.database import create_tables, SessionLocal
from models.patient import Patient
from models.appointment import Appointment
from models.vaccination import VaccinationSchedule
from models.vaccination_reminder import VaccinationReminder

# ─── Routers ──────────────────────────────────────────────────────────────────
from routers.inbound import router as inbound_router
from routers.outbound import router as outbound_router
from routers.patients import router as patients_router
from routers.stats import router as stats_router
from routers.simulate import router as simulate_router
from routers.calls import router as calls_router
from routers.vaccination import router as vaccination_router
from routers.vaccination_reminder import router as vaccination_reminder_router
from call_engine.twilio_router import router as twilio_router
from api.appointments import router as appointments_router

# ─── WebSocket / Media Stream ─────────────────────────────────────────────────
from dashboard.ws_broadcaster import connect_client, disconnect_client
from call_engine.media_stream import handle_media_stream

# ─── App Init ─────────────────────────────────────────────────────────────────
app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Include Routers ──────────────────────────────────────────────────────────
app.include_router(inbound_router)
app.include_router(outbound_router)
app.include_router(patients_router)
app.include_router(stats_router)
app.include_router(simulate_router)
app.include_router(calls_router)
app.include_router(vaccination_router)
app.include_router(vaccination_reminder_router)
app.include_router(twilio_router)
app.include_router(appointments_router)

# ─── WebSocket: Live Dashboard ────────────────────────────────────────────────
@app.websocket("/ws/dashboard")
async def dashboard_ws(websocket: WebSocket):
    await connect_client(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        disconnect_client(websocket)

# ─── WebSocket: Media Stream ──────────────────────────────────────────────────
@app.websocket("/ws/stream/{call_sid}")
async def media_stream_ws(websocket: WebSocket, call_sid: str):
    await handle_media_stream(websocket, call_sid)

# ─── Helper Functions ─────────────────────────────────────────────────────────
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
    try:
        return mapping.get(overall_risk_category.strip(), "GREEN")
    except:
        return "GREEN"

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

# ─── CSV Paths ────────────────────────────────────────────────────────────────
CSV_PATH     = os.path.join(os.path.dirname(__file__), "data", "patients.csv")
VAX_CSV_PATH = os.path.join(os.path.dirname(__file__), "data", "vaccination.csv")

# ─── Seed: Patients ───────────────────────────────────────────────────────────
def seed_patients_from_csv():
    if not os.path.exists(CSV_PATH):
        print(f"[Seed] patients.csv not found at {CSV_PATH}, skipping.")
        return

    db = SessionLocal()
    try:
        existing = db.query(Patient).count()
        if existing > 0:
            print(f"[Seed] DB already has {existing} patients, skipping.")
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
        print(f"[Seed] ❌ Patient seed failed: {e}")
    finally:
        db.close()

# ─── Seed: Vaccination Schedule ───────────────────────────────────────────────
def seed_vaccination_schedule():
    if not os.path.exists(VAX_CSV_PATH):
        print(f"[Seed] vaccination.csv not found at {VAX_CSV_PATH}, skipping.")
        return

    db = SessionLocal()
    try:
        existing = db.query(VaccinationSchedule).count()
        if existing > 0:
            print(f"[Seed] Vaccination schedule already seeded ({existing} records), skipping.")
            return

        age_to_weeks = {
            "Birth": 0, "6 weeks": 6, "10 weeks": 10,
            "14 weeks": 14, "9 months": 36, "12 months": 52,
        }

        with open(VAX_CSV_PATH, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            records = []
            for row in reader:
                age_label = row.get("Age", "").strip()
                records.append(VaccinationSchedule(
                    age_label=age_label,
                    age_weeks=age_to_weeks.get(age_label),
                    vaccine_name=row.get("Vaccine Name", "").strip(),
                    dose=safe_str(row.get("Dose", "")),
                    route_site=safe_str(row.get("Route/Site", "")),
                    remarks=safe_str(row.get("Remarks", "")),
                ))

        db.bulk_save_objects(records)
        db.commit()
        print(f"[Seed] ✅ Seeded {len(records)} vaccination records.")
    except Exception as e:
        db.rollback()
        print(f"[Seed] ❌ Vaccination seed failed: {e}")
    finally:
        db.close()

# ─── Startup ──────────────────────────────────────────────────────────────────
@app.on_event('startup')
async def startup():
    create_tables()
    print("[Startup] Database tables created successfully")
    seed_patients_from_csv()
    seed_vaccination_schedule()

# ─── Root ─────────────────────────────────────────────────────────────────────
@app.get('/')
def root():
    return {
        "message": f"{settings.APP_NAME} backend is running",
        "debug": settings.DEBUG,
        "docs": "/docs"
    }

@app.get('/health')
def health():
    return {"status": "ok"}