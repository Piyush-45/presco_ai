from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid
from sqlalchemy import delete
from app.database import get_db, AsyncSessionLocal
from app.models import Patient, Call
from app.services.plivo_service import PlivoService


router = APIRouter()

# Initialize Plivo service
plivo_service = PlivoService()

# Pydantic schemas
class PatientCreate(BaseModel):
    name: str
    phone: str  # E.164 format: +919876543210
    age: Optional[int] = None
    language: str = "english"
    custom_questions: Optional[str] = None
    patient_type: str = "opd"  # ADD THIS

class CallRequest(BaseModel):
    patient_id: int
class PatientUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    age: Optional[int] = None
    language: Optional[str] = None
    custom_questions: Optional[str] = None
    patient_type: Optional[str] = None  # ADD THIS


#! Create patient endpoint
@router.post("/patients")
async def create_patient(patient: PatientCreate, db: AsyncSession = Depends(get_db)):
    """Create a new patient"""
    from app.models import Patient
    from sqlalchemy.exc import IntegrityError

    # Check if phone already exists
    result = await db.execute(
        select(Patient).where(Patient.phone == patient.phone)
    )
    existing = result.scalar_one_or_none()

    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Patient with phone {patient.phone} already exists"
        )

    new_patient = Patient(
        name=patient.name,
        phone=patient.phone,
        age=patient.age,
        language=patient.language,
        custom_questions=patient.custom_questions,
        patient_type=patient.patient_type
    )

    db.add(new_patient)

    try:
        await db.commit()
        await db.refresh(new_patient)
        return new_patient
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create patient")

#! Get all patients
@router.get("/patients")
async def get_all_patients(db: AsyncSession = Depends(get_db)):
    """Get all patients with call counts"""
    from app.models import Patient, Call
    from sqlalchemy import func

    # Query patients with call count
    result = await db.execute(
        select(
            Patient,
            func.count(Call.id).label('call_count')
        )
        .outerjoin(Call, Patient.id == Call.patient_id)
        .group_by(Patient.id)
    )

    patients_data = []
    for patient, call_count in result.all():
        patients_data.append({
            "id": patient.id,
            "name": patient.name,
            "phone": patient.phone,
            "age": patient.age,
            "language": patient.language,
            "custom_questions": patient.custom_questions,
            "patient_type": patient.patient_type,
            "created_at": patient.created_at,
            "call_count": call_count
        })

    return {"patients": patients_data}

# !Update patient
@router.put("/patients/{patient_id}")
async def update_patient(
    patient_id: int,
    patient_update: PatientUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update patient information"""
    from app.models import Patient

    result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Update only provided fields
    if patient_update.name:
        patient.name = patient_update.name
    if patient_update.phone:
        patient.phone = patient_update.phone
    if patient_update.age:
        patient.age = patient_update.age
    if patient_update.language:
        patient.language = patient_update.language
    if patient_update.custom_questions is not None:
        patient.custom_questions = patient_update.custom_questions

    if patient_update.patient_type is not None:
      patient.patient_type = patient_update.patient_type


    await db.commit()
    await db.refresh(patient)

    return patient


 # !Delete patient
@router.delete("/patients/{patient_id}")
async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
    """Delete a patient and all associated calls"""
    from app.models import Patient, Call, Transcript

    # Get patient
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Delete associated transcripts first
    await db.execute(
        delete(Transcript).where(
            Transcript.call_id.in_(
                select(Call.id).where(Call.patient_id == patient_id)
            )
        )
    )

    # Delete associated calls
    await db.execute(
        delete(Call).where(Call.patient_id == patient_id)
    )

    # Delete patient
    await db.delete(patient)
    await db.commit()

    return {"message": "Patient deleted successfully"}
#! Initiate call to patient
@router.post("/initiate")
async def initiate_call(
    call_request: CallRequest,
    db: AsyncSession = Depends(get_db)
):
    """Initiate an outbound call to a patient"""

    # Validate Plivo credentials
    try:
        plivo_service.validate_credentials()
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Get patient from database
    result = await db.execute(
        select(Patient).where(Patient.id == call_request.patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Create call record with unique temporary ID
    temp_call_id = f"pending-{uuid.uuid4().hex[:8]}"

    new_call = Call(
        patient_id=patient.id,
        call_sid=temp_call_id,
        status="initiated"
    )
    db.add(new_call)
    await db.commit()
    await db.refresh(new_call)

    # Make the call via Plivo
    call_uuid = plivo_service.make_call(
        to_number=patient.phone,
        call_id=new_call.id
    )

    if call_uuid:
        # Update call record with Plivo UUID
        new_call.call_sid = call_uuid
        new_call.status = "ringing"
        await db.commit()

        return {
            "message": "Call initiated successfully",
            "call_id": new_call.id,
            "call_uuid": call_uuid,
            "patient": patient.name,
            "phone": patient.phone
        }
    else:
        # Call failed
        new_call.status = "failed"
        await db.commit()
        raise HTTPException(status_code=500, detail="Failed to initiate call")

# Plivo Answer Webhook - called when patient picks up
@router.post("/answer/{call_id}")
async def handle_answer(
    call_id: int,
    db: AsyncSession = Depends(get_db)
):
    """Plivo calls this webhook when the call is answered"""
    import os

    result = await db.execute(select(Call).where(Call.id == call_id))
    call = result.scalar_one_or_none()

    if not call:
        return Response(
            content="<Response><Hangup/></Response>",
            media_type="application/xml"
        )

    call.status = "answered"
    await db.commit()

    base_url = os.getenv("BASE_URL")
    if not base_url:
        print("ERROR: BASE_URL not set")
        return Response(content="<Response><Hangup/></Response>", media_type="application/xml")

    ws_url = f"{base_url.replace('https', 'wss')}/ws/plivo/{call_id}"
    xml_response = plivo_service.generate_answer_xml(ws_url)

    print(f"✅ Call {call_id} answered, streaming to: {ws_url}")

    return Response(content=xml_response, media_type="application/xml")

# Get all calls (with optional patient filter)
@router.get("/calls")
async def get_all_calls(
    patient_id: Optional[int] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get all calls, optionally filtered by patient_id"""

    if patient_id:
        # Get calls for specific patient
        result = await db.execute(
            select(Call, Patient)
            .join(Patient)
            .where(Call.patient_id == patient_id)
            .order_by(Call.started_at.desc())
        )
    else:
        # Get all calls
        result = await db.execute(
            select(Call, Patient)
            .join(Patient)
            .order_by(Call.started_at.desc())
        )

    rows = result.all()

    return {
        "count": len(rows),
        "calls": [
            {
                "call_id": call.id,
                "patient_id": call.patient_id,
                "patient_name": patient.name,
                "call_sid": call.call_sid,
                "status": call.status,
                "duration": call.duration,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            }
            for call, patient in rows
        ]
    }

# Get call history for a specific patient
@router.get("/patients/{patient_id}/calls")
async def get_patient_calls(patient_id: int, db: AsyncSession = Depends(get_db)):
    """Get all calls for a specific patient"""

    # Check if patient exists
    result = await db.execute(
        select(Patient).where(Patient.id == patient_id)
    )
    patient = result.scalar_one_or_none()

    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    # Get all calls for this patient
    result = await db.execute(
        select(Call)
        .where(Call.patient_id == patient_id)
        .order_by(Call.started_at.desc())
    )
    calls = result.scalars().all()

    return {
        "patient_id": patient_id,
        "patient_name": patient.name,
        "total_calls": len(calls),
        "calls": [
            {
                "call_id": call.id,
                "call_sid": call.call_sid,
                "status": call.status,
                "duration": call.duration,
                "cost": call.cost,
                "started_at": call.started_at.isoformat() if call.started_at else None,
                "ended_at": call.ended_at.isoformat() if call.ended_at else None,
            }
            for call in calls
        ]
    }
# Get call details
@router.get("/calls/{call_id}")
async def get_call(call_id: int, db: AsyncSession = Depends(get_db)):
    """Get details of a specific call"""
    result = await db.execute(
        select(Call).where(Call.id == call_id)
    )
    call = result.scalar_one_or_none()

    if not call:
        raise HTTPException(status_code=404, detail="Call not found")

    return {
        "id": call.id,
        "patient_id": call.patient_id,
        "call_sid": call.call_sid,
        "status": call.status,
        "duration": call.duration,
        "started_at": call.started_at
    }

# Get transcript for a call
@router.get("/calls/{call_id}/transcript")
async def get_transcript(call_id: int, db: AsyncSession = Depends(get_db)):
    """Get transcript for a specific call"""
    from app.models import Transcript
    import json

    result = await db.execute(
        select(Transcript).where(Transcript.call_id == call_id)
    )
    transcript = result.scalar_one_or_none()

    if not transcript:
        raise HTTPException(status_code=404, detail="Transcript not found")

    # Parse summary if it exists
    summary = None
    if transcript.summary:
        try:
            summary = json.loads(transcript.summary)
        except:
            summary = transcript.summary

    return {
        "call_id": call_id,
        "transcript": json.loads(transcript.full_transcript) if transcript.full_transcript else {},
        "summary": summary,  # Include summary
        "costs": {
            "stt": transcript.stt_cost,
            "llm": transcript.llm_cost,
            "tts": transcript.tts_cost
        },
        "created_at": transcript.created_at
    }
# WebSocket endpoint for Pipecat pipeline

# async def plivo_websocket(websocket: WebSocket, call_id: int):
#     """WebSocket for Pipecat-powered conversation"""

#     await websocket.accept()
#     print(f"WebSocket connected for call {call_id}")

#     try:
#         # Get patient info from database
#         async with AsyncSessionLocal() as db:
#             result = await db.execute(
#                 select(Patient, Call)
#                 .join(Call, Patient.id == Call.patient_id)
#                 .where(Call.id == call_id)
#             )
#             row = result.first()

#             if not row:
#                 print(f"No patient/call found for call_id {call_id}")
#                 await websocket.close()
#                 return

#             patient, call = row

#         print(f"Starting call for {patient.name}")

#         # Run the Pipecat pipeline
#         from app.services.pipeline_service import run_patient_call

#         await run_patient_call(
#             websocket=websocket,
#             patient_name=patient.name,
#             questions=patient.custom_questions or "How are you feeling today?"
#         )

#     except Exception as e:
#         print(f"Pipeline error: {e}")
#         import traceback
#         traceback.print_exc()
#     finally:
#         print(f"WebSocket closed for call {call_id}")




async def plivo_websocket(websocket: WebSocket, call_id: int):
    """WebSocket for Pipecat-powered conversation"""

    await websocket.accept()
    print(f"WebSocket connected for call {call_id}")

    # Create database session for this call
    async with AsyncSessionLocal() as db:
        try:
            # Get patient info
            result = await db.execute(
                select(Patient, Call)
                .join(Call, Patient.id == Call.patient_id)
                .where(Call.id == call_id)
            )
            row = result.first()

            if not row:
                print(f"No patient/call found for call_id {call_id}")
                await websocket.close()
                return

            patient, call = row

            print(f"Starting call for {patient.name}")

            # Use custom questions if available, otherwise default
            questions = patient.custom_questions if patient.custom_questions else "How are you feeling today?"

            # Run the Pipecat pipeline with patient-specific questions
            from app.services.pipeline_service import run_patient_call

            await run_patient_call(
                websocket=websocket,
                patient_name=patient.name,
                questions=questions,  # Now using actual patient questions
                call_id=call_id,
                db_session=db
            )

        except Exception as e:
            print(f"Pipeline error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print(f"WebSocket closed for call {call_id}")




# !!!! above one is working for english


# from fastapi import APIRouter, Depends, HTTPException, Request, WebSocket, WebSocketDisconnect
# from fastapi.responses import Response
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy import select
# from pydantic import BaseModel
# from typing import Optional
# from datetime import datetime
# import uuid
# from sqlalchemy import delete
# from app.database import get_db, AsyncSessionLocal
# from app.models import Patient, Call
# from app.services.plivo_service import PlivoService


# router = APIRouter()

# # Initialize Plivo service
# plivo_service = PlivoService()

# # Pydantic schemas
# class PatientCreate(BaseModel):
#     name: str
#     phone: str  # E.164 format: +919876543210
#     age: Optional[int] = None
#     language: str = "english"
#     custom_questions: Optional[str] = None
#     patient_type: str = "opd"  # ADD THIS

# class CallRequest(BaseModel):
#     patient_id: int
# class PatientUpdate(BaseModel):
#     name: Optional[str] = None
#     phone: Optional[str] = None
#     age: Optional[int] = None
#     language: Optional[str] = None
#     custom_questions: Optional[str] = None
#     patient_type: Optional[str] = None  # ADD THIS


# #! Create patient endpoint
# @router.post("/patients")
# async def create_patient(patient: PatientCreate, db: AsyncSession = Depends(get_db)):
#     """Create a new patient"""
#     from app.models import Patient
#     from sqlalchemy.exc import IntegrityError

#     # Check if phone already exists
#     result = await db.execute(
#         select(Patient).where(Patient.phone == patient.phone)
#     )
#     existing = result.scalar_one_or_none()

#     if existing:
#         raise HTTPException(
#             status_code=400,
#             detail=f"Patient with phone {patient.phone} already exists"
#         )

#     new_patient = Patient(
#         name=patient.name,
#         phone=patient.phone,
#         age=patient.age,
#         language=patient.language,
#         custom_questions=patient.custom_questions,
#         patient_type=patient.patient_type
#     )

#     db.add(new_patient)

#     try:
#         await db.commit()
#         await db.refresh(new_patient)
#         return new_patient
#     except IntegrityError:
#         await db.rollback()
#         raise HTTPException(status_code=400, detail="Failed to create patient")

# #! Get all patients
# @router.get("/patients")
# async def get_all_patients(db: AsyncSession = Depends(get_db)):
#     """Get all patients with call counts"""
#     from app.models import Patient, Call
#     from sqlalchemy import func

#     # Query patients with call count
#     result = await db.execute(
#         select(
#             Patient,
#             func.count(Call.id).label('call_count')
#         )
#         .outerjoin(Call, Patient.id == Call.patient_id)
#         .group_by(Patient.id)
#     )

#     patients_data = []
#     for patient, call_count in result.all():
#         patients_data.append({
#             "id": patient.id,
#             "name": patient.name,
#             "phone": patient.phone,
#             "age": patient.age,
#             "language": patient.language,
#             "custom_questions": patient.custom_questions,
#             "patient_type": patient.patient_type,
#             "created_at": patient.created_at,
#             "call_count": call_count
#         })

#     return {"patients": patients_data}

# # !Update patient
# @router.put("/patients/{patient_id}")
# async def update_patient(
#     patient_id: int,
#     patient_update: PatientUpdate,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Update patient information"""
#     from app.models import Patient

#     result = await db.execute(
#         select(Patient).where(Patient.id == patient_id)
#     )
#     patient = result.scalar_one_or_none()

#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Update only provided fields
#     if patient_update.name:
#         patient.name = patient_update.name
#     if patient_update.phone:
#         patient.phone = patient_update.phone
#     if patient_update.age:
#         patient.age = patient_update.age
#     if patient_update.language:
#         patient.language = patient_update.language
#     if patient_update.custom_questions is not None:
#         patient.custom_questions = patient_update.custom_questions

#     if patient_update.patient_type is not None:
#       patient.patient_type = patient_update.patient_type


#     await db.commit()
#     await db.refresh(patient)

#     return patient


#  # !Delete patient
# @router.delete("/patients/{patient_id}")
# async def delete_patient(patient_id: int, db: AsyncSession = Depends(get_db)):
#     """Delete a patient and all associated calls"""
#     from app.models import Patient, Call, Transcript

#     # Get patient
#     result = await db.execute(
#         select(Patient).where(Patient.id == patient_id)
#     )
#     patient = result.scalar_one_or_none()

#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Delete associated transcripts first
#     await db.execute(
#         delete(Transcript).where(
#             Transcript.call_id.in_(
#                 select(Call.id).where(Call.patient_id == patient_id)
#             )
#         )
#     )

#     # Delete associated calls
#     await db.execute(
#         delete(Call).where(Call.patient_id == patient_id)
#     )

#     # Delete patient
#     await db.delete(patient)
#     await db.commit()

#     return {"message": "Patient deleted successfully"}
# #! Initiate call to patient
# @router.post("/initiate")
# async def initiate_call(
#     call_request: CallRequest,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Initiate an outbound call to a patient"""

#     # Validate Plivo credentials
#     try:
#         plivo_service.validate_credentials()
#     except ValueError as e:
#         raise HTTPException(status_code=500, detail=str(e))

#     # Get patient from database
#     result = await db.execute(
#         select(Patient).where(Patient.id == call_request.patient_id)
#     )
#     patient = result.scalar_one_or_none()

#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Create call record with unique temporary ID
#     temp_call_id = f"pending-{uuid.uuid4().hex[:8]}"

#     new_call = Call(
#         patient_id=patient.id,
#         call_sid=temp_call_id,
#         status="initiated"
#     )
#     db.add(new_call)
#     await db.commit()
#     await db.refresh(new_call)

#     # Make the call via Plivo
#     call_uuid = plivo_service.make_call(
#         to_number=patient.phone,
#         call_id=new_call.id
#     )

#     if call_uuid:
#         # Update call record with Plivo UUID
#         new_call.call_sid = call_uuid
#         new_call.status = "ringing"
#         await db.commit()

#         return {
#             "message": "Call initiated successfully",
#             "call_id": new_call.id,
#             "call_uuid": call_uuid,
#             "patient": patient.name,
#             "phone": patient.phone
#         }
#     else:
#         # Call failed
#         new_call.status = "failed"
#         await db.commit()
#         raise HTTPException(status_code=500, detail="Failed to initiate call")

# # Plivo Answer Webhook - called when patient picks up
# @router.post("/answer/{call_id}")
# async def handle_answer(
#     call_id: int,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Plivo calls this webhook when the call is answered"""
#     import os

#     result = await db.execute(select(Call).where(Call.id == call_id))
#     call = result.scalar_one_or_none()

#     if not call:
#         return Response(
#             content="<Response><Hangup/></Response>",
#             media_type="application/xml"
#         )

#     call.status = "answered"
#     await db.commit()

#     base_url = os.getenv("BASE_URL")
#     if not base_url:
#         print("ERROR: BASE_URL not set")
#         return Response(content="<Response><Hangup/></Response>", media_type="application/xml")

#     ws_url = f"{base_url.replace('https', 'wss')}/ws/plivo/{call_id}"
#     xml_response = plivo_service.generate_answer_xml(ws_url)

#     print(f"✅ Call {call_id} answered, streaming to: {ws_url}")

#     return Response(content=xml_response, media_type="application/xml")

# # Get all calls (with optional patient filter)
# @router.get("/calls")
# async def get_all_calls(
#     patient_id: Optional[int] = None,
#     db: AsyncSession = Depends(get_db)
# ):
#     """Get all calls, optionally filtered by patient_id"""

#     if patient_id:
#         # Get calls for specific patient
#         result = await db.execute(
#             select(Call, Patient)
#             .join(Patient)
#             .where(Call.patient_id == patient_id)
#             .order_by(Call.started_at.desc())
#         )
#     else:
#         # Get all calls
#         result = await db.execute(
#             select(Call, Patient)
#             .join(Patient)
#             .order_by(Call.started_at.desc())
#         )

#     rows = result.all()

#     return {
#         "count": len(rows),
#         "calls": [
#             {
#                 "call_id": call.id,
#                 "patient_id": call.patient_id,
#                 "patient_name": patient.name,
#                 "call_sid": call.call_sid,
#                 "status": call.status,
#                 "duration": call.duration,
#                 "started_at": call.started_at.isoformat() if call.started_at else None,
#                 "ended_at": call.ended_at.isoformat() if call.ended_at else None,
#             }
#             for call, patient in rows
#         ]
#     }

# # Get call history for a specific patient
# @router.get("/patients/{patient_id}/calls")
# async def get_patient_calls(patient_id: int, db: AsyncSession = Depends(get_db)):
#     """Get all calls for a specific patient"""

#     # Check if patient exists
#     result = await db.execute(
#         select(Patient).where(Patient.id == patient_id)
#     )
#     patient = result.scalar_one_or_none()

#     if not patient:
#         raise HTTPException(status_code=404, detail="Patient not found")

#     # Get all calls for this patient
#     result = await db.execute(
#         select(Call)
#         .where(Call.patient_id == patient_id)
#         .order_by(Call.started_at.desc())
#     )
#     calls = result.scalars().all()

#     return {
#         "patient_id": patient_id,
#         "patient_name": patient.name,
#         "total_calls": len(calls),
#         "calls": [
#             {
#                 "call_id": call.id,
#                 "call_sid": call.call_sid,
#                 "status": call.status,
#                 "duration": call.duration,
#                 "cost": call.cost,
#                 "started_at": call.started_at.isoformat() if call.started_at else None,
#                 "ended_at": call.ended_at.isoformat() if call.ended_at else None,
#             }
#             for call in calls
#         ]
#     }
# # Get call details
# @router.get("/calls/{call_id}")
# async def get_call(call_id: int, db: AsyncSession = Depends(get_db)):
#     """Get details of a specific call"""
#     result = await db.execute(
#         select(Call).where(Call.id == call_id)
#     )
#     call = result.scalar_one_or_none()

#     if not call:
#         raise HTTPException(status_code=404, detail="Call not found")

#     return {
#         "id": call.id,
#         "patient_id": call.patient_id,
#         "call_sid": call.call_sid,
#         "status": call.status,
#         "duration": call.duration,
#         "started_at": call.started_at
#     }

# # Get transcript for a call
# @router.get("/calls/{call_id}/transcript")
# async def get_transcript(call_id: int, db: AsyncSession = Depends(get_db)):
#     """Get transcript for a specific call"""
#     from app.models import Transcript
#     import json

#     result = await db.execute(
#         select(Transcript).where(Transcript.call_id == call_id)
#     )
#     transcript = result.scalar_one_or_none()

#     if not transcript:
#         raise HTTPException(status_code=404, detail="Transcript not found")

#     # Parse summary if it exists
#     summary = None
#     if transcript.summary:
#         try:
#             summary = json.loads(transcript.summary)
#         except:
#             summary = transcript.summary

#     return {
#         "call_id": call_id,
#         "transcript": json.loads(transcript.full_transcript) if transcript.full_transcript else {},
#         "summary": summary,  # Include summary
#         "costs": {
#             "stt": transcript.stt_cost,
#             "llm": transcript.llm_cost,
#             "tts": transcript.tts_cost
#         },
#         "created_at": transcript.created_at
#     }
# # WebSocket endpoint for Pipecat pipeline

# # Keep all existing imports and functions...
# # Only replace the plivo_websocket function:

# async def plivo_websocket(websocket: WebSocket, call_id: int):
#     """WebSocket for Pipecat-powered conversation"""

#     await websocket.accept()
#     print(f"WebSocket connected for call {call_id}")

#     async with AsyncSessionLocal() as db:
#         try:
#             result = await db.execute(
#                 select(Patient, Call)
#                 .join(Call, Patient.id == Call.patient_id)
#                 .where(Call.id == call_id)
#             )
#             row = result.first()

#             if not row:
#                 print(f"No patient/call found for call_id {call_id}")
#                 await websocket.close()
#                 return

#             patient, call = row

#             print(f"Starting call for {patient.name} in {patient.language}")

#             questions = patient.custom_questions if patient.custom_questions else "How are you feeling today?"

#             from app.services.pipeline_service import run_patient_call

#             await run_patient_call(
#                 websocket=websocket,
#                 patient_name=patient.name,
#                 questions=questions,
#                 call_id=call_id,
#                 db_session=db,
#                 patient_language=patient.language  # Pass language here
#             )

#         except Exception as e:
#             print(f"Pipeline error: {e}")
#             import traceback
#             traceback.print_exc()
#         finally:
#             print(f"WebSocket closed for call {call_id}")
