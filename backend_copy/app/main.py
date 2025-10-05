from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv
from openai import OpenAI, AuthenticationError

from app.database import init_db
from app.routers import calls

# Load environment variables
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
print("🔑 OpenAI Key Loaded:", "Yes" if api_key else "No")

# ---- Helper: Verify OpenAI Key ----
def verify_openai_key():
    if not api_key:
        print("❌ Missing OPENAI_API_KEY in .env file.")
        return False

    try:
        client = OpenAI(api_key=api_key)
        # Try fetching a lightweight resource (models list)
        _ = client.models.list()
        print("✅ OpenAI API key verified successfully.")
        return True
    except AuthenticationError:
        print("❌ Invalid OpenAI API key. Please check your .env file.")
        return False
    except Exception as e:
        print(f"⚠️ Could not verify OpenAI API key: {e}")
        return False

# ---- Lifespan context manager ----
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up... Initializing database")
    await init_db()
    print("✅ Database initialized")

    print("🧠 Verifying OpenAI API key...")
    key_ok = verify_openai_key()
    if not key_ok:
        print("⚠️ Warning: OpenAI key invalid or missing. Voice agent may fail later.")

    yield
    # Shutdown
    print("👋 Shutting down...")

# ---- Create FastAPI app ----
app = FastAPI(
    title="Voice Agent API",
    description="AI-powered conversational voice agent for patient follow-ups",
    version="1.0.0",
    lifespan=lifespan
)

# ---- CORS ----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---- Routers ----
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])

# ---- WebSocket ----
@app.websocket("/ws/plivo/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: int):
    """WebSocket proxy to the router function"""
    await calls.plivo_websocket(websocket, call_id)

# ---- Health endpoints ----
@app.get("/")
async def root():
    return {
        "message": "Voice Agent API is running",
        "status": "healthy",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    return {"status": "ok"}
