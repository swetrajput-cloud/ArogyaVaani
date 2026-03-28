# 🏥 AarogyaVaani
**AI-Powered Multilingual Indic Voice Patient Engagement Platform**
HackMatrix 2.0 — NIT Goa | Track 3: Healthcare AI

---

## 🚀 What It Does
AarogyaVaani makes automated voice calls to patients in their local language (Hindi, Marathi, Bengali, Tamil, Telugu, Gujarati), collects health responses, runs AI-powered NLP analysis, and flags high-risk patients for doctor escalation — all in real time.

## 🧠 AI Stack
- **Groq (Llama3)** — Clinical NLP: intent extraction, severity scoring, symptom detection
- **Sarvam AI** — Indic STT + TTS for voice calls
- **Twilio** — Outbound voice calls + real-time media streaming

## 📦 Tech Stack
| Layer | Tech |
|---|---|
| Backend | FastAPI + PostgreSQL + SQLAlchemy |
| Frontend | React + Vite + Tailwind CSS |
| Voice | Twilio Media Streams + Sarvam AI |
| NLP | Groq (Llama3-8b) |
| Real-time | WebSockets |

## 🗂️ Project Structure
```
arogya vaani new/
├── backend/
│   ├── main.py
│   ├── config.py
│   ├── models/
│   ├── routers/
│   ├── nlp/
│   ├── sarvam/
│   ├── modules/
│   ├── call_engine/
│   ├── dashboard/
│   └── data/patients.csv
├── frontend/
│   └── src/
│       ├── pages/
│       ├── components/
│       ├── hooks/
│       └── api/
```

## ⚙️ Setup

### Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
# Create .env file with your keys (see .env.example)
uvicorn main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment Variables (.env inside backend/)
```
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_PHONE_NUMBER=
SARVAM_API_KEY=
ANTHROPIC_API_KEY=
GROQ_API_KEY=
DATABASE_URL=postgresql://postgres:yourpassword@localhost:5432/yourdbname
SECRET_KEY=your_secret_key
WS_SECRET=your_ws_secret
```

## 🎯 Key Features
- 📞 Automated outbound voice calls in 6 Indian languages
- 🧠 Real-time AI clinical NLP (severity, sentiment, symptom detection)
- 🚨 Automatic escalation for RED risk patients
- 👨‍👩‍👦 Caregiver proxy routing for elderly patients
- 📊 Live dashboard with risk distribution charts
- 🎙️ Call simulator for demo without real phone calls
- 📋 Full call history with NLP breakdown per patient

## 📊 Dataset
120 real patient records from health camps:
- Gandhi Maidan Morning Jilo Health Camp
- Digha Slum Health Camp  
- Aashrya Old Age Home
- Disha Deaddiction Center

## 👥 Team
NIT Goa — HackMatrix 2.0