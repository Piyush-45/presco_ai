# from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
# from sqlalchemy.orm import relationship
# from datetime import datetime
# from app.database import Base

# class Patient(Base):
#     __tablename__ = "patients"

#     id = Column(Integer, primary_key=True, index=True)
#     name = Column(String(100), nullable=False)
#     phone = Column(String(15), nullable=False, unique=True)  # E.164 format: +919876543210
#     age = Column(Integer, nullable=True)
#     language = Column(String(10), default="english")  # 'english' or 'hindi'
#     custom_questions = Column(Text, nullable=True)  # JSON string of questions
#     patient_type = Column(String, default="opd")
#     created_at = Column(DateTime, default=datetime.utcnow)

#     # Relationship: one patient can have many calls
#     calls = relationship("Call", back_populates="patient", cascade="all, delete-orphan")

# class Call(Base):
#     __tablename__ = "calls"

#     id = Column(Integer, primary_key=True, index=True)
#     patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
#     call_sid = Column(String(100), unique=True, nullable=False)  # Plivo call UUID
#     status = Column(String(20), default="initiated")  # initiated, ringing, answered, completed, failed
#     duration = Column(Integer, default=0)  # in seconds
#     cost = Column(Float, default=0.0)  # total cost in USD
#     started_at = Column(DateTime, default=datetime.utcnow)
#     ended_at = Column(DateTime, nullable=True)

#     # Relationship
#     patient = relationship("Patient", back_populates="calls")
#     transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")

# class Transcript(Base):
#     __tablename__ = "transcripts"

#     id = Column(Integer, primary_key=True, index=True)
#     call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, unique=True)
#     full_transcript = Column(Text, nullable=True)  # Complete conversation JSON
#     summary = Column(Text, nullable=True)  # AI-generated summary
#     stt_cost = Column(Float, default=0.0)  # Deepgram cost
#     llm_cost = Column(Float, default=0.0)  # OpenAI GPT cost
#     tts_cost = Column(Float, default=0.0)  # TTS cost
#     created_at = Column(DateTime, default=datetime.utcnow)

#     # Relationship
#     call = relationship("Call", back_populates="transcript")


from sqlalchemy import Column, Integer, String, DateTime, Text, Float, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    phone = Column(String(15), nullable=False, unique=True)
    age = Column(Integer, nullable=True)
    language = Column(String(20), default="english")  # Added length
    custom_questions = Column(Text, nullable=True)
    patient_type = Column(String(20), default="opd")  # Added length
    created_at = Column(DateTime, default=datetime.utcnow)

    calls = relationship("Call", back_populates="patient", cascade="all, delete-orphan")


class Call(Base):
    __tablename__ = "calls"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"), nullable=False)
    call_sid = Column(String(100), unique=True, nullable=False)
    status = Column(String(20), default="initiated")  # Added length
    duration = Column(Integer, default=0)
    cost = Column(Float, default=0.0)
    started_at = Column(DateTime, default=datetime.utcnow)
    ended_at = Column(DateTime, nullable=True)

    patient = relationship("Patient", back_populates="calls")
    transcript = relationship("Transcript", back_populates="call", uselist=False, cascade="all, delete-orphan")


class Transcript(Base):
    __tablename__ = "transcripts"

    id = Column(Integer, primary_key=True, index=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, unique=True)
    full_transcript = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    stt_cost = Column(Float, default=0.0)
    llm_cost = Column(Float, default=0.0)
    tts_cost = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)

    call = relationship("Call", back_populates="transcript")
