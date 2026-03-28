from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import sys, os, csv
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from routers.inbound import router as inbound_router
from routers.outbound import router as outbound_router
from config import settings
from models.database import create_tables, SessionLocal
from models.patient import Patient
from call_engine.twiml_router import router as twilio_router
from routers.patients import router as patients_router
from routers.stats import router as stats_router
from routers.simulate import router as simulate_router
from routers.calls import router as calls_router
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
app.include_router(patients_router)
app.include_router(stats_router)
app.include_router(simulate_router)
app.include_router(calls_router)
app.include_router(inbound_router)
app.include_router(outbound_router)

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

# ─── Startup ──────────────────────────────────────────────────────────────────

@app.on_event('startup')
async def startup():
    create_tables()
    print("[Startup] Database tables created successfully")
    seed_patients_from_csv()

# ─── Root ─────────────────────────────────────────────────────────────────────

@app.get('/')
def root():
    return {
        "message": f"{settings.APP_NAME} backend is running",
        "debug": settings.DEBUG,
        "docs": "http://localhost:8000/docs"
    }

@app.get('/health')
def health():
    return {"status": "ok"}