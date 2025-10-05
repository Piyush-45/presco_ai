# # Update patient
# @router.put("/patients/{patient_id}")
# async def update_patient(
#     patient_id: int,
#     patient_update: PatientCreate,
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

#     await db.commit()
#     await db.refresh(patient)

#     return patient
