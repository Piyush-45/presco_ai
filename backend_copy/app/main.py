from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from app.database import init_db
from app.routers import calls

# Load environment variables
load_dotenv()

# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting up... Initializing database")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("👋 Shutting down...")

# Create FastAPI app
app = FastAPI(
    title="Voice Agent API",
    description="AI-powered conversational voice agent for patient follow-ups",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(calls.router, prefix="/api/calls", tags=["Calls"])

# IMPORTANT: Register WebSocket route at app level
@app.websocket("/ws/plivo/{call_id}")
async def websocket_endpoint(websocket: WebSocket, call_id: int):
    """WebSocket proxy to the router function"""
    await calls.plivo_websocket(websocket, call_id)

# Health check endpoints
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
