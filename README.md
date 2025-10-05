# 🏥 AI Voice Agent for Hospitals

An AI-powered **hospital voice assistant** that can make outbound calls to patients (OPD / Discharged) for follow-ups, feedback, and reminders.  
Built with **FastAPI (backend)**, **Next.js (frontend)**, and integrates with **Plivo, Deepgram, OpenAI, ElevenLabs**.

---

## ✨ Features
- 📞 Outbound patient calls using **Plivo Telephony**
- 🗣️ Real-time AI conversation with **Deepgram STT + OpenAI + ElevenLabs TTS**
- 🧠 Custom hospital-specific follow-up questions
- 📊 Call summaries with sentiment analysis + cost tracking
- 💾 Transcript storage with structured insights
- 🌐 Modern dashboard (Next.js + Tailwind)

---

## 🛠️ Tech Stack
- **Backend**: FastAPI, SQLAlchemy, SQLite (dev) / Postgres (prod)
- **Frontend**: Next.js 14, React, TailwindCSS
- **AI Services**: 
  - Deepgram (Speech-to-Text)
  - OpenAI GPT-4o-mini (Conversational AI)
  - ElevenLabs (Text-to-Speech)
- **Telephony**: Plivo (WebSocket streaming)
- **Infra**: Python venv, Node.js, Nginx, AWS-ready

---

## 📂 Project Structure
```bash
python-ai-agent-hospital-project/
│
├── backend/       # FastAPI app (calls, patients, transcripts, DB)
├── frontend/      # Next.js dashboard
└── .gitignore

```


🚀 Getting Started
1️⃣ Clone the repo
```
git clone https://github.com/Piyush-45/python-ai-hospital
cd python-ai-agent-hospital-project
```


2️⃣ Backend Setup
```
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a .env file in /backend:

```
PLIVO_AUTH_ID=xxxx
PLIVO_AUTH_TOKEN=xxxx
PLIVO_PHONE_NUMBER=+91xxxx
OPENAI_API_KEY=sk-xxxx
DEEPGRAM_API_KEY=dg-xxxx
ELEVENLABS_API_KEY=el-xxxx
ELEVENLABS_VOICE_ID=h061KGyOtpLYDxcoi8E3
BASE_URL=http://localhost:8000
```
```
PLIVO_AUTH_ID=xxxx
PLIVO_AUTH_TOKEN=xxxx
PLIVO_PHONE_NUMBER=+91xxxx
OPENAI_API_KEY=sk-xxxx
DEEPGRAM_API_KEY=dg-xxxx
ELEVENLABS_API_KEY=el-xxxx
ELEVENLABS_VOICE_ID=h061KGyOtpLYDxcoi8E3

BASE_URL=http://localhost:8000
```

``` uvicorn app.main:app --reload --port 8000``` 


3️⃣ Frontend Setup
```
cd ../frontend
npm install
npm run dev

Frontend runs at: 👉 http://localhost:3000
Backend runs at: 👉 http://localhost:8000
```

🖥️ Deployment (AWS)
```
Recommended production setup:
OS: Ubuntu 22.04 LTS
Web Server: Nginx (with WebSocket support for /ws/plivo/)
DB: SQLite (testing) → Postgres (production, e.g., AWS RDS)
Reverse Proxy: Nginx proxying FastAPI + Next.js, WebSocket pass-through
SSL: Let’s Encrypt (Certbot)
````

✅ Testing

Add a patient in the dashboard.
Initiate an outbound call.
Verify AI conversation + transcript saved.
Check Call Cost Breakdown in dashboard.

👨‍💻 Author
Built by Piyush Tyagi
